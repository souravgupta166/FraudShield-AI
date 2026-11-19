from datetime import datetime, timezone

from sqlalchemy import func, select, update

from src.data.bitcoin_ingestion import ingest_confirmed_transaction
from src.data.database_models import BitcoinBlock, BitcoinTransaction
from src.data.mempool_client import MempoolClient


PAGE_SIZE = 25


def _verify_canonical_block(
    client: MempoolClient,
    height: int,
    block_hash: str,
) -> None:
    """Verify that a block remains in the best chain."""

    canonical_hash = client.get_block_hash_at_height(height)

    if canonical_hash.lower() != block_hash.lower():
        raise ValueError(
            f"Block reorganisation detected at height {height}"
        )

    status = client.get_block_status(block_hash)

    if (
        not isinstance(status, dict)
        or status.get("in_best_chain") is not True
    ):
        raise ValueError(
            f"Block {block_hash} is no longer in the best chain"
        )


def process_block_page(
    session_factory,
    client: MempoolClient,
    block_hash: str,
) -> dict:
    """
    Process one verified page of transactions from a canonical block.

    Transaction records are persisted individually through the existing
    atomic ingestion function. The block cursor advances only after the
    complete page has been validated and persisted.
    """

    with session_factory() as session:
        block = session.get(BitcoinBlock, block_hash)

        if block is None:
            raise ValueError(f"Unknown block: {block_hash}")

        if not block.is_canonical:
            raise ValueError("Cannot process a non-canonical block")

        height = block.height
        expected_tx_count = block.tx_count
        start_index = block.next_transaction_index

        if not 0 <= start_index <= expected_tx_count:
            raise ValueError("Invalid block transaction cursor")

    _verify_canonical_block(client, height, block_hash)

    txids = client.get_block_txids(block_hash)

    if len(txids) != expected_tx_count:
        raise ValueError(
            "Block transaction count does not match its metadata"
        )

    if len(set(txids)) != len(txids):
        raise ValueError("Block transaction list contains duplicate IDs")

    if start_index == expected_tx_count:
        with session_factory() as session:
            with session.begin():
                session.execute(
                    update(BitcoinBlock)
                    .where(
                        BitcoinBlock.block_hash == block_hash,
                        BitcoinBlock.is_canonical.is_(True),
                    )
                    .values(
                        ingestion_status="completed",
                        ingestion_error=None,
                        last_ingested_at=datetime.now(timezone.utc),
                    )
                )

        return {
            "block_hash": block_hash,
            "height": height,
            "transactions_processed": 0,
            "next_transaction_index": start_index,
            "status": "completed",
        }

    expected_page = txids[
        start_index : start_index + PAGE_SIZE
    ]

    transactions = client.get_block_transactions(
        block_hash,
        start_index,
    )

    returned_txids = [transaction.txid for transaction in transactions]

    if returned_txids != expected_page:
        raise ValueError(
            "Downloaded transaction page does not match "
            "the expected ordered block transaction IDs"
        )

    for transaction in transactions:
        if (
            transaction.status.get("confirmed") is not True
            or transaction.status.get("block_hash") != block_hash
        ):
            raise ValueError(
                f"Transaction {transaction.txid} does not belong "
                "to the expected confirmed block"
            )

    block_data = client.get_block(block_hash)

    for transaction in transactions:
        ingest_confirmed_transaction(
            transaction=transaction,
            session_factory=session_factory,
            client=client,
            block_data=block_data,
        )

    # Verify the block again after transaction persistence.
    _verify_canonical_block(client, height, block_hash)

    next_index = start_index + len(transactions)

    with session_factory() as session:
        with session.begin():
            current_block = session.get(BitcoinBlock, block_hash)

            if current_block is None or not current_block.is_canonical:
                raise ValueError(
                    "Block became non-canonical before progress update"
                )

            if current_block.next_transaction_index != start_index:
                raise ValueError(
                    "Block cursor changed during page processing"
                )

            stored_count = session.scalar(
                select(func.count())
                .select_from(BitcoinTransaction)
                .where(
                    BitcoinTransaction.block_hash == block_hash,
                    BitcoinTransaction.status == "confirmed",
                )
            )

            completed = next_index == expected_tx_count

            current_block.next_transaction_index = next_index
            current_block.ingested_transaction_count = stored_count
            current_block.ingestion_status = (
                "completed" if completed else "partial"
            )
            current_block.last_ingested_at = datetime.now(timezone.utc)
            current_block.ingestion_error = None

    return {
        "block_hash": block_hash,
        "height": height,
        "transactions_processed": len(transactions),
        "next_transaction_index": next_index,
        "ingested_transaction_count": stored_count,
        "status": "completed" if completed else "partial",
    }
