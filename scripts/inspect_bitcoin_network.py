from src.data.mempool_client import MempoolClient


def main():
    with MempoolClient() as client:
        print("FRAUDSHIELD AI — BITCOIN TRANSACTION INVESTIGATION")
        print("=" * 58)

        height = client.get_tip_height()
        block_hash = client.get_tip_hash()
        block = client.get_block(block_hash)

        print(f"Block height       : {height}")
        print(f"Block hash         : {block_hash}")
        print(f"Block transactions : {block.get('tx_count')}")

        txids = client.get_recent_mempool_txids()
        source = "mempool"

        if not txids:
            print("\nNo recent mempool transaction IDs returned.")
            print("Searching confirmed block for a normal transaction.")

            txids = client.get_block_txids(block_hash)
            source = "confirmed block"

        transaction = None

        # Inspect at most 10 candidates to avoid unnecessary API requests.
        for txid in txids[:10]:
            candidate = client.get_transaction(txid)

            is_coinbase = any(
                item.get("is_coinbase", False)
                for item in candidate.vin
            )

            if not is_coinbase:
                transaction = candidate
                break

        if transaction is None:
            print("No ordinary transaction found in the first 10 candidates.")
            return

        print("\nTRANSACTION DETAILS")
        print("-" * 58)
        print(f"Source             : {source}")
        print(f"Transaction ID     : {transaction.txid}")
        print(f"Version            : {transaction.version}")
        print(f"Size               : {transaction.size} bytes")
        print(f"Weight             : {transaction.weight}")
        print(f"Fee                : {transaction.fee} satoshis")
        print(f"Input count        : {len(transaction.vin)}")
        print(f"Output count       : {len(transaction.vout)}")
        print(f"Confirmed          : {transaction.status.get('confirmed')}")

        print("\nINPUTS")
        for index, item in enumerate(transaction.vin):
            prevout = item.get("prevout") or {}
            print(f"\nInput {index}")
            print(f"  Previous txid    : {item.get('txid')}")
            print(f"  Previous vout    : {item.get('vout')}")
            print(f"  Previous value   : {prevout.get('value')} satoshis")
            print(f"  Previous address : {prevout.get('scriptpubkey_address')}")

        print("\nOUTPUTS")
        for index, item in enumerate(transaction.vout):
            print(f"\nOutput {index}")
            print(f"  Value            : {item.get('value')} satoshis")
            print(f"  Script type      : {item.get('scriptpubkey_type')}")
            print(f"  Address          : {item.get('scriptpubkey_address')}")
            print(f"  Locking script   : {item.get('scriptpubkey')}")

        print("\nSUCCESS: Ordinary Bitcoin transaction retrieved and validated.")


if __name__ == "__main__":
    main()
