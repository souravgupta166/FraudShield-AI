
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.bitcoin_ingestion import ingest_confirmed_transaction
from src.data.mempool_client import MempoolClient


# Maximum number of successful transactions per run.
MAX_TRANSACTIONS = 10

# Maximum number of block transactions to inspect.
# This allows us to skip coinbase and problematic candidates.
MAX_CANDIDATES = 50


def main():

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError(
            "DATABASE_URL environment variable is not configured"
        )

    engine = create_engine(
        database_url,
        pool_pre_ping=True,
    )

    SessionLocal = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    successful = []
    failed = []
    skipped = 0
    inspected = 0

    try:

        with MempoolClient() as client:

            print("\nFRAUDSHIELD AI — BITCOIN BATCH INGESTION")
            print("=" * 65)

            # 1. Retrieve the latest Bitcoin block.

            tip_height = client.get_tip_height()
            block_hash = client.get_tip_hash()

            print(f"Current block height : {tip_height}")
            print(f"Current block hash   : {block_hash}")
            print(f"Target transactions  : {MAX_TRANSACTIONS}")
            print(f"Candidate scan limit : {MAX_CANDIDATES}")

            # 2. Retrieve transaction IDs from the latest block.

            txids = client.get_block_txids(block_hash)

            print(f"Transactions in block: {len(txids)}")
            print("\nStarting transaction inspection...\n")

            # 3. Inspect candidates and ingest valid transactions.

            for txid in txids[:MAX_CANDIDATES]:

                if len(successful) >= MAX_TRANSACTIONS:
                    break

                inspected += 1

                print(
                    f"[{inspected}/{MAX_CANDIDATES}] "
                    f"Inspecting {txid}"
                )

                try:

                    transaction = client.get_transaction(txid)

                    is_coinbase = any(
                        item.get("is_coinbase", False)
                        for item in transaction.vin
                    )

                    is_confirmed = (
                        transaction.status.get("confirmed") is True
                        and transaction.status.get("block_hash") is not None
                    )

                    if is_coinbase or not is_confirmed:

                        skipped += 1

                        print("  SKIPPED: Coinbase or unconfirmed transaction")
                        continue

                    # 4. Validate and persist transaction data.

                    result = ingest_confirmed_transaction(
                        transaction=transaction,
                        session_factory=SessionLocal,
                        client=client,
                    )

                    successful.append(result)

                    print("  INGESTED SUCCESSFULLY")
                    print(f"  Fee: {result['accounting']['calculated_fee_sats']} sats")
                    print(f"  Inputs saved: {result['inputs_saved']}")
                    print(f"  Outputs saved: {result['outputs_saved']}")

                except Exception as exc:

                    failed.append({
                        "txid": txid,
                        "error": str(exc)[:500],
                    })

                    print(f"  FAILED: {str(exc)[:300]}")

            # 5. Print final batch summary.

            print("\n")
            print("=" * 65)
            print("BITCOIN BATCH INGESTION SUMMARY")
            print("=" * 65)

            print(f"Block height             : {tip_height}")
            print(f"Candidates inspected     : {inspected}")
            print(f"Successfully ingested    : {len(successful)}")
            print(f"Skipped                  : {skipped}")
            print(f"Failed                   : {len(failed)}")
            print(f"Target batch size        : {MAX_TRANSACTIONS}")

            if successful:

                print("\nSUCCESSFUL TRANSACTIONS")

                for result in successful:

                    print(
                        f"- {result['txid']} "
                        f"| {result['inputs_saved']} inputs "
                        f"| {result['outputs_saved']} outputs"
                    )

            if failed:

                print("\nFAILED TRANSACTIONS")

                for item in failed:

                    print(f"- {item['txid']}: {item['error']}")

            if len(successful) == MAX_TRANSACTIONS:

                print("\nSUCCESS: Target batch size reached.")

            elif successful:

                print(
                    "\nPARTIAL SUCCESS: Some transactions were ingested, "
                    "but the target batch size was not reached."
                )

            else:

                print("\nWARNING: No transactions were ingested.")

                raise RuntimeError(
                    "Batch ingestion completed without a successful transaction."
                )

    finally:

        engine.dispose()


if __name__ == "__main__":
    main()
