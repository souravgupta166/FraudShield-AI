
import argparse
import os

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.data.bitcoin_ingestion import ingest_confirmed_transaction
from src.data.mempool_client import MempoolClient


MAX_BLOCKS_PER_RUN = 10
MAX_TRANSACTIONS_PER_BLOCK = 25
MAX_CANDIDATES_PER_BLOCK = 50


def parse_args():
    parser = argparse.ArgumentParser(
        description="Ingest confirmed Bitcoin transactions from historical blocks."
    )
    parser.add_argument(
        "--start-height",
        type=int,
        required=True,
        help="First Bitcoin block height (inclusive).",
    )
    parser.add_argument(
        "--end-height",
        type=int,
        required=True,
        help="Last Bitcoin block height (inclusive).",
    )
    return parser.parse_args()


def main():
    args = parse_args()

    if args.start_height < 0 or args.end_height < args.start_height:
        raise ValueError("Invalid block height range.")

    block_count = args.end_height - args.start_height + 1

    if block_count > MAX_BLOCKS_PER_RUN:
        raise ValueError(
            f"Maximum range is {MAX_BLOCKS_PER_RUN} blocks per run."
        )

    database_url = os.environ.get("DATABASE_URL")

    if not database_url:
        raise RuntimeError("DATABASE_URL environment variable is not configured.")

    engine = create_engine(database_url, pool_pre_ping=True)
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)

    total_successful = 0
    total_skipped = 0
    total_failed = 0

    try:
        with MempoolClient() as client:
            tip_height = client.get_tip_height()

            if args.end_height > tip_height:
                raise ValueError(
                    f"End height {args.end_height} exceeds current tip {tip_height}."
                )

            print("\nFRAUDSHIELD AI — HISTORICAL BITCOIN INGESTION")
            print("=" * 70)
            print(f"Current Bitcoin tip : {tip_height}")
            print(f"Requested range     : {args.start_height} to {args.end_height}")
            print(f"Blocks to process   : {block_count}")
            print(f"Success limit/block: {MAX_TRANSACTIONS_PER_BLOCK}")
            print(f"Candidate limit/block: {MAX_CANDIDATES_PER_BLOCK}")

            for height in range(args.start_height, args.end_height + 1):
                successful = 0
                skipped = 0
                failed = 0

                print("\n" + "=" * 70)
                print(f"PROCESSING BLOCK HEIGHT {height}")
                print("=" * 70)

                try:
                    block_hash = client.get_block_hash_at_height(height)
                    block_data = client.get_block(block_hash)

                    if block_data.get("id", "").lower() != block_hash:
                        raise ValueError("Block metadata hash mismatch.")

                    if block_data.get("height") != height:
                        raise ValueError("Block metadata height mismatch.")

                    txids = client.get_block_txids(block_hash)

                    print(f"Canonical block hash : {block_hash}")
                    print(f"Transactions in block: {len(txids)}")

                except Exception as exc:
                    print(f"BLOCK FAILED: {str(exc)[:300]}")
                    total_failed += 1
                    continue

                candidates = txids[:MAX_CANDIDATES_PER_BLOCK]

                for index, txid in enumerate(candidates, start=1):
                    if successful >= MAX_TRANSACTIONS_PER_BLOCK:
                        break

                    print(f"\n[{index}/{len(candidates)}] Inspecting {txid}")

                    try:
                        transaction = client.get_transaction(txid)

                        is_coinbase = any(
                            item.get("is_coinbase", False)
                            for item in transaction.vin
                        )

                        status = transaction.status
                        transaction_block_hash = status.get("block_hash")

                        if is_coinbase:
                            skipped += 1
                            print("  SKIPPED: Coinbase transaction")
                            continue

                        if status.get("confirmed") is not True:
                            skipped += 1
                            print("  SKIPPED: Transaction is not confirmed")
                            continue

                        if (
                            not isinstance(transaction_block_hash, str)
                            or transaction_block_hash.lower() != block_hash
                        ):
                            skipped += 1
                            print("  SKIPPED: Transaction block hash mismatch")
                            continue

                        result = ingest_confirmed_transaction(
                            transaction=transaction,
                            session_factory=SessionLocal,
                            client=client,
                            block_data=block_data,
                        )

                        successful += 1
                        print("  INGESTED SUCCESSFULLY")
                        print(
                            f"  Fee: {result['accounting']['calculated_fee_sats']} sats"
                        )
                        print(f"  Inputs saved: {result['inputs_saved']}")
                        print(f"  Outputs saved: {result['outputs_saved']}")

                    except Exception as exc:
                        failed += 1
                        print(f"  FAILED: {str(exc)[:300]}")

                total_successful += successful
                total_skipped += skipped
                total_failed += failed

                print(f"\nBlock {height} summary:")
                print(f"  Ingested: {successful}")
                print(f"  Skipped : {skipped}")
                print(f"  Failed  : {failed}")

            print("\n" + "=" * 70)
            print("HISTORICAL INGESTION SUMMARY")
            print("=" * 70)
            print(f"Blocks requested       : {block_count}")
            print(f"Transactions ingested  : {total_successful}")
            print(f"Transactions skipped   : {total_skipped}")
            print(f"Transaction failures   : {total_failed}")

            if total_successful == 0:
                raise RuntimeError("No transactions were successfully ingested.")

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()