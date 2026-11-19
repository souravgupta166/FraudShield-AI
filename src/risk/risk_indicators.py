from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class RiskThresholds:
    """
    Configurable investigation thresholds.

    These are operational rules, not calibrated fraud thresholds.
    """

    high_input_count: int
    high_output_count: int

    def __post_init__(self) -> None:
        if self.high_input_count < 2:
            raise ValueError("high_input_count must be at least 2")

        if self.high_output_count < 2:
            raise ValueError("high_output_count must be at least 2")


def evaluate_transaction_indicators(
    features: Mapping[str, Any],
    thresholds: RiskThresholds,
) -> list[dict[str, Any]]:
    """
    Evaluate explainable transaction investigation indicators.

    Findings are not proof of fraud or criminal activity.
    Missing data is not interpreted as zero.
    """

    findings: list[dict[str, Any]] = []

    txid = features.get("txid")

    input_count = features.get("input_count")

    if (
        isinstance(input_count, int)
        and not isinstance(input_count, bool)
        and input_count >= thresholds.high_input_count
    ):
        findings.append(
            {
                "indicator_code": "large_input_consolidation",
                "category": "transaction_structure",
                "severity": "informational",
                "title": "Large input consolidation",
                "description": (
                    "The transaction combines a relatively large "
                    "number of previous outputs."
                ),
                "evidence": {
                    "input_count": input_count,
                    "threshold": thresholds.high_input_count,
                },
                "caveat": (
                    "Input consolidation can be a legitimate wallet "
                    "management activity. This finding alone does "
                    "not indicate illicit activity."
                ),
            }
        )

    output_count = features.get("output_count")

    if (
        isinstance(output_count, int)
        and not isinstance(output_count, bool)
        and output_count >= thresholds.high_output_count
    ):
        findings.append(
            {
                "indicator_code": "high_output_count",
                "category": "transaction_structure",
                "severity": "informational",
                "title": "High output count",
                "description": (
                    "The transaction distributes value across "
                    "a relatively large number of outputs."
                ),
                "evidence": {
                    "output_count": output_count,
                    "threshold": thresholds.high_output_count,
                },
                "caveat": (
                    "Multiple outputs can occur in ordinary "
                    "payments, batching and exchange operations. "
                    "This finding is not proof of suspicious activity."
                ),
            }
        )

    fee_reconciliation_valid = features.get(
        "fee_reconciliation_valid"
    )

    if fee_reconciliation_valid is False:
        findings.append(
            {
                "indicator_code": "fee_reconciliation_mismatch",
                "category": "data_integrity",
                "severity": "warning",
                "title": "Fee reconciliation mismatch",
                "description": (
                    "The recorded transaction fee does not equal "
                    "the known input value minus output value."
                ),
                "evidence": {
                    "input_value_sats": features.get(
                        "input_value_sats"
                    ),
                    "output_value_sats": features.get(
                        "output_value_sats"
                    ),
                    "recorded_fee_sats": features.get("fee_sats"),
                },
                "caveat": (
                    "Investigate missing, incorrect or inconsistent "
                    "transaction data before drawing conclusions."
                ),
            }
        )

    if features.get("input_values_complete") is False:
        findings.append(
            {
                "indicator_code": "incomplete_input_value_data",
                "category": "data_quality",
                "severity": "informational",
                "title": "Incomplete input value data",
                "description": (
                    "One or more previous output values are "
                    "unavailable in the observed transaction data."
                ),
                "evidence": {
                    "input_count": input_count,
                    "input_values_complete": False,
                },
                "caveat": (
                    "Missing input values must not be interpreted "
                    "as zero or used for fee reconciliation."
                ),
            }
        )

    for finding in findings:
        finding["txid"] = txid

    return findings
