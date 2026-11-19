from sqlalchemy import select, update

from src.data.bitcoin_ingestion import (
    _build_block_upsert_statement,
    _resolve_block_metadata,
)
from src.data.database_models import BitcoinBlock, BitcoinTransaction
from src.data.mempool_client import MempoolClient


def discover_recent_canonical_blocks(
    session_factory,
    client: MempoolClient,
    scan_depth: int = 3,
) -> list[dict]:
    """Discover and verify recent canonical blocks, including reorg changes."""

    if isinstance(scan_depth, bool) or not isinstance(scan_depth, int):
        raise ValueError("Scan depth must be an integer")

    if not 1 <= scan_depth <= 12:
        raise ValueError("Scan depth must be between 1 and 12")

    tip_height = client.get_tip_height()

    if (
        isinstance(tip_height, bool)
        or not isinstance(tip_height, int)
        or tip_height < 0
    ):
        raise ValueError("Bitcoin API returned an invalid tip height")

    first_height = max(0, tip_height - scan_depth + 1)
    discovered = []

    for height in range(first_height, tip_height + 1):
        block_hash = client.get_block_hash_at_height(height)
        block_data = client.get_block(block_hash)

        _, block_time, metadata_height, tx_count = (
            _resolve_block_metadata(
                block_hash,
                client,
                block_data,
            )
        )

        if metadata_height != height:
            raise ValueError(
                f"Block metadata height mismatch at height {height}"
            )

        block_status = client.get_block_status(block_hash)

        if (
            not isinstance(block_status, dict)
            or not isinstance(block_status.get("in_best_chain"), bool)
        ):
            raise ValueError(
                "Block status is missing a valid in_best_chain flag"
            )

        if block_status["in_best_chain"] is not True:
            raise ValueError(
                f"Block at height {height} is not in the best chain"
            )

        with session_factory() as session:
            with session.begin():
                previous_blocks = session.scalars(
                    select(BitcoinBlock).where(
                        BitcoinBlock.height == height,
                        BitcoinBlock.block_hash != block_hash,
                        BitcoinBlock.is_canonical.is_(True),
                    )
                ).all()

                previous_hashes = [
                    block.block_hash for block in previous_blocks
                ]

                if previous_hashes:
                    session.execute(
                        update(BitcoinBlock)
                        .where(
                            BitcoinBlock.block_hash.in_(previous_hashes)
                        )
                        .values(is_canonical=False)
                    )

                    session.execute(
                        update(BitcoinTransaction)
                        .where(
                            BitcoinTransaction.block_hash.in_(
                                previous_hashes
                            ),
                            BitcoinTransaction.status == "confirmed",
                        )
                        .values(status="orphaned")
                    )

                statement = _build_block_upsert_statement(
                    block_hash=block_hash,
                    block_height=height,
                    block_data=block_data,
                    block_time=block_time,
                    tx_count=tx_count,
                )

                session.execute(statement)

                # Discovery has independently verified canonicality.
                session.execute(
                    update(BitcoinBlock)
                    .where(BitcoinBlock.block_hash == block_hash)
                    .values(is_canonical=True)
                )

                # A previously orphaned block may become canonical again.
                session.execute(
                    update(BitcoinTransaction)
                    .where(
                        BitcoinTransaction.block_hash == block_hash,
                        BitcoinTransaction.status == "orphaned",
                    )
                    .values(status="confirmed")
                )

        discovered.append(
            {
                "height": height,
                "block_hash": block_hash,
                "tx_count": tx_count,
                "is_canonical": True,
                "replaced_block_hashes": previous_hashes,
            }
        )

    return discovered
