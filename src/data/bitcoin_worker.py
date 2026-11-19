import logging
import signal
import threading
from typing import Callable

from sqlalchemy import update

from src.data.bitcoin_block_discovery import discover_recent_canonical_blocks
from src.data.bitcoin_block_processor import process_block_page
from src.data.database_models import BitcoinBlock
from src.data.mempool_client import MempoolClient
from src.data.worker_runtime import (
    WorkerConfig,
    create_worker_database,
    release_worker_lock,
    try_acquire_worker_lock,
)


logger = logging.getLogger("fraudshield.worker")


def mark_block_failed(session_factory, block_hash: str, error: Exception) -> None:
    """Record a page-processing failure without changing the cursor."""

    message = f"{type(error).__name__}: {error}"[:2000]

    with session_factory() as session:
        with session.begin():
            session.execute(
                update(BitcoinBlock)
                .where(
                    BitcoinBlock.block_hash == block_hash,
                    BitcoinBlock.is_canonical.is_(True),
                )
                .values(
                    ingestion_status="failed",
                    ingestion_error=message,
                )
            )


def run_ingestion_cycle(
    session_factory,
    client: MempoolClient,
    config: WorkerConfig,
    stop_event: threading.Event,
) -> dict:
    """Discover recent blocks and process pages in round-robin order."""

    discovered = discover_recent_canonical_blocks(
        session_factory=session_factory,
        client=client,
        scan_depth=config.scan_depth,
    )

    pages_processed = 0
    transactions_processed = 0
    failed_blocks = []

    # Newest first, but rotate across all discovered blocks.
    active_blocks = list(reversed(discovered))

    while active_blocks and pages_processed < config.max_pages_per_cycle:
        if stop_event.is_set():
            break

        for block_info in list(active_blocks):
            if stop_event.is_set():
                break

            if pages_processed >= config.max_pages_per_cycle:
                break

            block_hash = block_info["block_hash"]

            try:
                result = process_block_page(
                    session_factory=session_factory,
                    client=client,
                    block_hash=block_hash,
                )

                processed_count = result["transactions_processed"]

                if processed_count > 0:
                    pages_processed += 1
                    transactions_processed += processed_count

                    logger.info(
                        "Processed block height=%s hash=%s "
                        "transactions=%s cursor=%s status=%s",
                        result["height"],
                        block_hash,
                        processed_count,
                        result["next_transaction_index"],
                        result["status"],
                    )

                    if config.page_delay_seconds > 0:
                        if stop_event.wait(config.page_delay_seconds):
                            break

                if result["status"] == "completed":
                    active_blocks.remove(block_info)
                elif processed_count == 0:
                    logger.warning(
                        "Block made no progress: height=%s hash=%s",
                        block_info["height"],
                        block_hash,
                    )
                    active_blocks.remove(block_info)

            except Exception as exc:
                try:
                    mark_block_failed(
                        session_factory,
                        block_hash,
                        exc,
                    )
                except Exception:
                    logger.exception(
                        "Could not record failure for block %s",
                        block_hash,
                    )

                failed_blocks.append(
                    {
                        "height": block_info["height"],
                        "block_hash": block_hash,
                        "error": str(exc),
                    }
                )

                logger.exception(
                    "Block processing failed: height=%s hash=%s",
                    block_info["height"],
                    block_hash,
                )

                active_blocks.remove(block_info)

            if stop_event.is_set():
                break

    summary = {
        "blocks_discovered": len(discovered),
        "pages_processed": pages_processed,
        "transactions_processed": transactions_processed,
        "failed_blocks": len(failed_blocks),
    }

    logger.info("Ingestion cycle finished: %s", summary)
    return summary


def run_worker(
    config: WorkerConfig,
    stop_event: threading.Event,
    client_factory: Callable = MempoolClient,
) -> None:
    """Run the continuous ingestion worker under a PostgreSQL advisory lock."""

    engine, session_factory = create_worker_database(config.database_url)
    lock_connection = None

    try:
        logger.info("Starting Bitcoin ingestion worker")

        while not stop_event.is_set():
            lock_connection = try_acquire_worker_lock(engine)

            if lock_connection is not None:
                logger.info("Acquired PostgreSQL worker advisory lock")
                break

            logger.warning(
                "Another worker holds the advisory lock; retrying in %s seconds",
                config.poll_interval_seconds,
            )

            if stop_event.wait(config.poll_interval_seconds):
                return

        if stop_event.is_set():
            return

        with client_factory() as client:
            while not stop_event.is_set():
                try:
                    run_ingestion_cycle(
                        session_factory=session_factory,
                        client=client,
                        config=config,
                        stop_event=stop_event,
                    )
                except Exception:
                    logger.exception("Ingestion cycle failed")

                if not stop_event.is_set():
                    logger.info(
                        "Next ingestion cycle in %s seconds",
                        config.poll_interval_seconds,
                    )
                    stop_event.wait(config.poll_interval_seconds)

    finally:
        if lock_connection is not None:
            release_worker_lock(lock_connection)
            logger.info("Released PostgreSQL worker advisory lock")

        engine.dispose()
        logger.info("Bitcoin ingestion worker stopped")


def main() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )

    stop_event = threading.Event()

    def request_shutdown(signum, frame):
        logger.info("Received shutdown signal %s", signum)
        stop_event.set()

    signal.signal(signal.SIGINT, request_shutdown)
    signal.signal(signal.SIGTERM, request_shutdown)

    config = WorkerConfig.from_env()
    run_worker(config, stop_event)


if __name__ == "__main__":
    main()
