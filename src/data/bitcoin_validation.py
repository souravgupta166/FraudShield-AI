from collections.abc import Mapping
from typing import Any


def _require_satoshis(value: Any, field: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"{field} must be a non-negative integer")

    return value


def validate_transaction_accounting(
    transaction: Mapping[str, Any],
) -> dict[str, Any]:
    """
    Validate Bitcoin transaction input/output accounting.

    For ordinary transactions:
        input value = output value + transaction fee

    Coinbase transactions are handled separately because their inputs
    do not spend previous transaction outputs.
    """

    vin = transaction.get("vin")
    vout = transaction.get("vout")

    if not isinstance(vin, list) or not vin:
        raise ValueError("Transaction must contain at least one input")

    if not isinstance(vout, list) or not vout:
        raise ValueError("Transaction must contain at least one output")

    output_total = sum(
        _require_satoshis(item.get("value"), f"Output {index} value")
        for index, item in enumerate(vout)
    )

    coinbase_inputs = [
        item for item in vin if item.get("is_coinbase", False)
    ]

    if coinbase_inputs:
        if len(vin) != 1 or len(coinbase_inputs) != 1:
            raise ValueError("Coinbase transaction must have exactly one coinbase input")

        return {
            "is_coinbase": True,
            "input_total_sats": None,
            "output_total_sats": output_total,
            "declared_fee_sats": transaction.get("fee"),
            "calculated_fee_sats": None,
            "accounting_valid": None,
            "message": "Coinbase transaction: ordinary input/output fee check not applicable",
        }

    input_total = 0

    for index, item in enumerate(vin):
        if not isinstance(item, Mapping):
            raise ValueError(f"Input {index} must be an object")

        prevout = item.get("prevout")

        if not isinstance(prevout, Mapping):
            raise ValueError(f"Input {index} is missing previous output data")

        input_total += _require_satoshis(
            prevout.get("value"),
            f"Input {index} previous output value",
        )

    declared_fee = _require_satoshis(
        transaction.get("fee"),
        "Transaction fee",
    )

    calculated_fee = input_total - output_total

    if calculated_fee < 0:
        raise ValueError("Outputs exceed the total input value")

    if calculated_fee != declared_fee:
        raise ValueError(
            f"Fee mismatch: calculated {calculated_fee} sats, "
            f"API reports {declared_fee} sats"
        )

    return {
        "is_coinbase": False,
        "input_total_sats": input_total,
        "output_total_sats": output_total,
        "declared_fee_sats": declared_fee,
        "calculated_fee_sats": calculated_fee,
        "accounting_valid": True,
        "message": "Input, output and fee accounting reconciles",
    }
