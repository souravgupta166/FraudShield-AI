from datetime import datetime, timezone
import uuid
from typing import Callable

from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from src.data.bitcoin_validation import validate_transaction_accounting
from src.data.database_models import (
    BitcoinBlock,
    BitcoinIngestionRun,
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
)
from src.data.mempool_client import MempoolClient


def _resolve_block_metadata(
    block_hash: str,
    client: MempoolClient,
    block_data: dict | None = None,
) -> tuple[dict, datetime, int, int]:
    """Fetch when needed and validate metadata for a confirmed block."""
    if block_data is None:
        block_data = client.get_block(block_hash)

    if not isinstance(block_data, dict):
        raise ValueError("Block metadata must be a dictionary")

    response_hash = block_data.get("id")
    if (
        not isinstance(response_hash, str)
        or response_hash.lower() != block_hash.lower()
    ):
        raise ValueError("Block response hash does not match requested hash")

    timestamp = block_data.get("timestamp")
    if isinstance(timestamp, bool) or not isinstance(timestamp, int):
        raise ValueError("Block has an invalid timestamp")

    block_time = datetime.fromtimestamp(timestamp, tz=timezone.utc)

    block_height = block_data.get("height")
    if (
        isinstance(block_height, bool)
        or not isinstance(block_height, int)
        or block_height < 0
    ):
        raise ValueError("Block has an invalid height")

    tx_count = block_data.get("tx_count")
    if (
        isinstance(tx_count, bool)
        or not isinstance(tx_count, int)
        or tx_count < 0
    ):
        raise ValueError("Block has an invalid transaction count")

    return block_data, block_time, block_height, tx_count


def _build_block_upsert_statement(
    block_hash: str,
    block_height: int,
    block_data: dict,
    block_time: datetime,
    tx_count: int,
):
    """Build a block upsert without overwriting existing canonical status."""
    statement = insert(BitcoinBlock).values(
        block_hash=block_hash,
        height=block_height,
        previous_block_hash=block_data.get("previousblockhash"),
        block_time=block_time,
        tx_count=tx_count,
        is_canonical=True,
    )

    return statement.on_conflict_do_update(
        index_elements=[BitcoinBlock.block_hash],
        set_={
            "height": statement.excluded.height,
            "previous_block_hash": statement.excluded.previous_block_hash,
            "block_time": statement.excluded.block_time,
            "tx_count": statement.excluded.tx_count,
        },
    )


def ingest_confirmed_transaction(
    transaction: BitcoinTransaction,
    session_factory: Callable[[], Session],
    client: MempoolClient,
    block_data: dict | None = None,
) -> dict:
    """
    Validate and persist one confirmed Bitcoin transaction.

    The block, transaction, inputs and outputs are persisted atomically.
    Repeated ingestion updates existing records instead of duplicating them.
    """

    txid = transaction.txid
    status = transaction.status

    if status.get("confirmed") is not True:
        raise ValueError("Only confirmed transactions can be ingested")

    block_hash = status.get("block_hash")

    if not isinstance(block_hash, str) or len(block_hash) != 64:
        raise ValueError("Confirmed transaction has no valid block hash")

    accounting = validate_transaction_accounting(
        transaction.model_dump()
    )

    block_data, block_time, block_height, tx_count = (
        _resolve_block_metadata(block_hash, client, block_data)
    )

    run_id = uuid.uuid4()

    # Record the ingestion attempt independently so failures are retained.
    with session_factory() as session:
        session.add(
            BitcoinIngestionRun(
                run_id=run_id,
                source="mempool.space",
                status="running",
                metadata_json={
                    "txid": txid,
                    "block_hash": block_hash,
                    "block_height": block_height,
                },
            )
        )
        session.commit()

    try:
        with session_factory() as session:
            with session.begin():

                # 1. Persist the containing block.
                session.execute(
                    _build_block_upsert_statement(
                        block_hash=block_hash,
                        block_height=block_height,
                        block_data=block_data,
                        block_time=block_time,
                        tx_count=tx_count,
                    )
                )

                # 2. Persist the transaction.
                tx_payload = transaction.model_dump(mode="json")

                tx_statement = insert(BitcoinTransaction).values(
                    txid=txid,
                    wtxid=tx_payload.get("wtxid"),
                    version=transaction.version,
                    locktime=transaction.locktime,
                    size=transaction.size,
                    weight=transaction.weight,
                    fee_sats=transaction.fee,
                    status="confirmed",
                    block_hash=block_hash,
                    raw_payload=tx_payload,
                )

                session.execute(
                    tx_statement.on_conflict_do_update(
                        index_elements=[BitcoinTransaction.txid],
                        set_={
                            "wtxid": tx_statement.excluded.wtxid,
                            "version": tx_statement.excluded.version,
                            "locktime": tx_statement.excluded.locktime,
                            "size": tx_statement.excluded.size,
                            "weight": tx_statement.excluded.weight,
                            "fee_sats": tx_statement.excluded.fee_sats,
                            "status": "confirmed",
                            "block_hash": block_hash,
                            "raw_payload": tx_statement.excluded.raw_payload,
                        },
                    )
                )

                # 3. Persist transaction inputs.
                for index, item in enumerate(transaction.vin):
                    prevout = item.get("prevout") or {}
                    is_coinbase = bool(item.get("is_coinbase", False))

                    input_values = {
                        "txid": txid,
                        "input_index": index,
                        "previous_txid": None if is_coinbase else item.get("txid"),
                        "previous_output_index": (
                            None if is_coinbase else item.get("vout")
                        ),
                        "sequence": item.get("sequence"),
                        "is_coinbase": is_coinbase,
                        "script_sig_hex": item.get("scriptsig"),
                        "witness_data": item.get("witness"),
                        "prevout_value_sats": (
                            None if is_coinbase else prevout.get("value")
                        ),
                        "prevout_script_pubkey_hex": (
                            None if is_coinbase else prevout.get("scriptpubkey")
                        ),
                        "prevout_address": (
                            None if is_coinbase
                            else prevout.get("scriptpubkey_address")
                        ),
                    }

                    input_statement = insert(
                        BitcoinTransactionInput
                    ).values(**input_values)

                    session.execute(
                        input_statement.on_conflict_do_update(
                            index_elements=[
                                BitcoinTransactionInput.txid,
                                BitcoinTransactionInput.input_index,
                            ],
                            set_={
                                key: value
                                for key, value in input_values.items()
                                if key not in ("txid", "input_index")
                            },
                        )
                    )

                # 4. Persist transaction outputs.
                for index, item in enumerate(transaction.vout):
                    output_values = {
                        "txid": txid,
                        "output_index": index,
                        "value_sats": item["value"],
                        "script_pubkey_hex": item["scriptpubkey"],
                        "script_type": item.get("scriptpubkey_type"),
                        "address": item.get("scriptpubkey_address"),
                    }

                    output_statement = insert(
                        BitcoinTransactionOutput
                    ).values(**output_values)

                    session.execute(
                        output_statement.on_conflict_do_update(
                            index_elements=[
                                BitcoinTransactionOutput.txid,
                                BitcoinTransactionOutput.output_index,
                            ],
                            set_={
                                key: value
                                for key, value in output_values.items()
                                if key not in ("txid", "output_index")
                            },
                        )
                    )

                # 5. Mark the ingestion run as completed.
                session.execute(
                    update(BitcoinIngestionRun)
                    .where(BitcoinIngestionRun.run_id == run_id)
                    .values(
                        status="completed",
                        finished_at=datetime.now(timezone.utc),
                        blocks_processed=1,
                        transactions_processed=1,
                    )
                )

        return {
            "run_id": str(run_id),
            "txid": txid,
            "block_hash": block_hash,
            "block_height": block_height,
            "inputs_saved": len(transaction.vin),
            "outputs_saved": len(transaction.vout),
            "accounting": accounting,
            "status": "completed",
        }

    except Exception as exc:
        # The transaction-data changes have been rolled back.
        # Record the failed attempt separately.
        with session_factory() as session:
            with session.begin():
                session.execute(
                    update(BitcoinIngestionRun)
                    .where(BitcoinIngestionRun.run_id == run_id)
                    .values(
                        status="failed",
                        finished_at=datetime.now(timezone.utc),
                        error_message=str(exc)[:4000],
                    )
                )

        raise