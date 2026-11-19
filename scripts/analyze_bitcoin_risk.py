from __future__ import annotations

import json
import os

from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from src.data.database_models import (
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
)
from src.risk.transaction_features import extract_transaction_features
from src.risk.risk_indicators import (
    RiskThresholds,
    evaluate_transaction_indicators,
)


HIGH_INPUT_COUNT = 10
HIGH_OUTPUT_COUNT = 10
MAX_TRANSACTIONS = 100


def main() -> None:
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

    thresholds = RiskThresholds(
        high_input_count=HIGH_INPUT_COUNT,
        high_output_count=HIGH_OUTPUT_COUNT,
    )

    analysed = 0
    findings_count = 0
    transactions_with_findings = 0
    unevaluable = 0

    try:
        with SessionLocal() as session:
            statement = (
                select(BitcoinTransaction)
                .where(BitcoinTransaction.status == "confirmed")
                .order_by(BitcoinTransaction.txid)
                .limit(MAX_TRANSACTIONS)
            )

            transactions = session.scalars(statement).all()

            print("\nFRAUDSHIELD AI — BITCOIN RISK ANALYSIS")
            print("=" * 75)
            print(f"Transactions selected : {len(transactions)}")
            print(f"Input threshold       : {HIGH_INPUT_COUNT}")
            print(f"Output threshold      : {HIGH_OUTPUT_COUNT}")
            print("Database mode         : READ ONLY")
            print("=" * 75)

            if not transactions:
                print("\nNo confirmed transactions found.")
                return

            for transaction in transactions:
                analysed += 1
                txid = transaction.txid

                inputs = session.scalars(
                    select(BitcoinTransactionInput)
                    .where(BitcoinTransactionInput.txid == txid)
                    .order_by(BitcoinTransactionInput.input_index)
                ).all()

                outputs = session.scalars(
                    select(BitcoinTransactionOutput)
                    .where(BitcoinTransactionOutput.txid == txid)
                    .order_by(BitcoinTransactionOutput.output_index)
                ).all()

                features = extract_transaction_features(
                    transaction=transaction,
                    inputs=inputs,
                    outputs=outputs,
                )

                findings = evaluate_transaction_indicators(
                    features=features,
                    thresholds=thresholds,
                )

                print(f"\n[{analysed}/{len(transactions)}]")
                print(f"Transaction ID : {txid}")
                print(f"Block hash     : {transaction.block_hash}")
                print(f"Inputs         : {features['input_count']}")
                print(f"Outputs        : {features['output_count']}")
                print(f"Fee            : {features['fee_sats']} sats")
                print(
                    "Fee rate       : "
                    f"{features['fee_rate_sat_vb']} sats/vB"
                )
                print(
                    "Input values   : "
                    f"{features['input_values_complete']}"
                )
                print(
                    "Fee reconciled : "
                    f"{features['fee_reconciliation_valid']}"
                )
                print(
                    "Output entropy : "
                    f"{features['output_value_entropy']}"
                )

                if not features["input_values_complete"]:
                    unevaluable += 1

                if findings:
                    transactions_with_findings += 1
                    findings_count += len(findings)

                    print("\n  INVESTIGATION FINDINGS")

                    for finding in findings:
                        print(
                            f"  - [{finding['severity'].upper()}] "
                            f"{finding['title']}"
                        )
                        print(f"    Code: {finding['indicator_code']}")
                        print(
                            "    Evidence: "
                            + json.dumps(
                                finding["evidence"],
                                sort_keys=True,
                            )
                        )
                        print(f"    Caveat: {finding['caveat']}")

                else:
                    print("\n  No configured indicators triggered.")

            print("\n")
            print("=" * 75)
            print("BITCOIN RISK ANALYSIS SUMMARY")
            print("=" * 75)
            print(f"Transactions analysed        : {analysed}")
            print(
                "Transactions with findings  : "
                f"{transactions_with_findings}"
            )
            print(f"Total findings               : {findings_count}")
            print(f"Incomplete input datasets    : {unevaluable}")
            print(
                "Transactions without findings: "
                f"{analysed - transactions_with_findings}"
            )
            print("=" * 75)

            print(
                "\nIMPORTANT: These are explainable investigation indicators, "
                "not fraud determinations."
            )

    finally:
        engine.dispose()


if __name__ == "__main__":
    main()
