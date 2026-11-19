
from __future__ import annotations

import math
from typing import Any, Sequence

from src.data.database_models import (
    BitcoinTransaction,
    BitcoinTransactionInput,
    BitcoinTransactionOutput,
)


def calculate_output_value_entropy(
    outputs: Sequence[BitcoinTransactionOutput],
) -> float | None:
    """
    Calculate Shannon entropy across transaction output values.

    Returns None when there are no outputs or the total output
    value is zero.

    Entropy describes output-value distribution. It does not
    establish whether a transaction is suspicious.
    """

    values = [
        output.value_sats
        for output in outputs
        if output.value_sats > 0
    ]

    total_value = sum(values)

    if not values or total_value == 0:
        return None

    probabilities = [
        value / total_value
        for value in values
    ]

    return -sum(
        probability * math.log2(probability)
        for probability in probabilities
    )


def extract_transaction_features(
    transaction: BitcoinTransaction,
    inputs: Sequence[BitcoinTransactionInput],
    outputs: Sequence[BitcoinTransactionOutput],
) -> dict[str, Any]:
    """
    Extract explainable features from an observed Bitcoin transaction.

    Missing input values are not treated as zero.
    Address counts include only addresses actually observed.
    """

    input_values = [
        item.prevout_value_sats
        for item in inputs
    ]

    all_input_values_known = (
        len(inputs) > 0
        and all(value is not None for value in input_values)
    )

    input_value_sats = (
        sum(input_values)
        if all_input_values_known
        else None
    )

    output_value_sats = sum(
        item.value_sats
        for item in outputs
    )

    virtual_size = (
        (transaction.weight + 3) // 4
        if transaction.weight is not None
        else None
    )

    fee_rate_sat_vb = None

    if (
        transaction.fee_sats is not None
        and virtual_size is not None
        and virtual_size > 0
    ):
        fee_rate_sat_vb = (
            transaction.fee_sats / virtual_size
        )

    input_addresses = {
        item.prevout_address
        for item in inputs
        if item.prevout_address
    }

    output_addresses = {
        item.address
        for item in outputs
        if item.address
    }

    fee_reconciliation_valid = None

    if (
        input_value_sats is not None
        and transaction.fee_sats is not None
    ):
        fee_reconciliation_valid = (
            input_value_sats - output_value_sats
            == transaction.fee_sats
        )

    return {
        "txid": transaction.txid,
        "status": transaction.status,
        "block_hash": transaction.block_hash,
        "fee_sats": transaction.fee_sats,
        "size_bytes": transaction.size,
        "weight": transaction.weight,
        "virtual_size_vbytes": virtual_size,
        "fee_rate_sat_vb": fee_rate_sat_vb,
        "input_count": len(inputs),
        "output_count": len(outputs),
        "input_values_complete": all_input_values_known,
        "input_value_sats": input_value_sats,
        "output_value_sats": output_value_sats,
        "unique_input_addresses": len(input_addresses),
        "unique_output_addresses": len(output_addresses),
        "coinbase_input_count": sum(
            item.is_coinbase
            for item in inputs
        ),
        "output_value_entropy": calculate_output_value_entropy(
            outputs
        ),
        "fee_reconciliation_valid": fee_reconciliation_valid,
    }
