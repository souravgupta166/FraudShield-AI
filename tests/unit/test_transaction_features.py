from types import SimpleNamespace

import pytest

from src.risk.transaction_features import (
    calculate_output_value_entropy,
    extract_transaction_features,
)


def make_transaction(**overrides):
    values = {
        "txid": "a" * 64,
        "status": "confirmed",
        "block_hash": "b" * 64,
        "fee_sats": 1_000,
        "size": 250,
        "weight": 600,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_input(**overrides):
    values = {
        "prevout_value_sats": 10_000,
        "prevout_address": "bc1qinput",
        "is_coinbase": False,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_output(**overrides):
    values = {
        "value_sats": 9_000,
        "address": "bc1qoutput",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_fee_rate_uses_virtual_size():
    features = extract_transaction_features(
        make_transaction(fee_sats=1_000, weight=600),
        [make_input()],
        [make_output(value_sats=9_000)],
    )

    assert features["virtual_size_vbytes"] == 150
    assert features["fee_rate_sat_vb"] == pytest.approx(1000 / 150)


def test_input_and_output_values_are_calculated():
    features = extract_transaction_features(
        make_transaction(fee_sats=1_000),
        [
            make_input(prevout_value_sats=6_000),
            make_input(prevout_value_sats=4_000),
        ],
        [
            make_output(value_sats=7_000),
            make_output(value_sats=2_000),
        ],
    )

    assert features["input_count"] == 2
    assert features["output_count"] == 2
    assert features["input_value_sats"] == 10_000
    assert features["output_value_sats"] == 9_000
    assert features["fee_reconciliation_valid"] is True


def test_missing_input_value_is_not_treated_as_zero():
    features = extract_transaction_features(
        make_transaction(),
        [
            make_input(prevout_value_sats=10_000),
            make_input(prevout_value_sats=None),
        ],
        [make_output(value_sats=9_000)],
    )

    assert features["input_values_complete"] is False
    assert features["input_value_sats"] is None
    assert features["fee_reconciliation_valid"] is None


def test_single_output_entropy_is_zero():
    entropy = calculate_output_value_entropy(
        [make_output(value_sats=9_000)]
    )

    assert entropy == pytest.approx(0.0)


def test_equal_outputs_have_entropy_of_one_bit():
    entropy = calculate_output_value_entropy(
        [
            make_output(value_sats=5_000),
            make_output(value_sats=5_000),
        ]
    )

    assert entropy == pytest.approx(1.0)


def test_zero_value_outputs_return_none_entropy():
    entropy = calculate_output_value_entropy(
        [make_output(value_sats=0)]
    )

    assert entropy is None


def test_fee_reconciliation_detects_mismatch():
    features = extract_transaction_features(
        make_transaction(fee_sats=1_000),
        [make_input(prevout_value_sats=10_000)],
        [make_output(value_sats=8_500)],
    )

    assert features["fee_reconciliation_valid"] is False


def test_no_outputs_returns_zero_output_total():
    features = extract_transaction_features(
        make_transaction(),
        [make_input()],
        [],
    )

    assert features["output_count"] == 0
    assert features["output_value_sats"] == 0
    assert features["output_value_entropy"] is None


def test_duplicate_addresses_are_counted_once():
    features = extract_transaction_features(
        make_transaction(),
        [
            make_input(prevout_address="bc1qsame"),
            make_input(prevout_address="bc1qsame"),
        ],
        [
            make_output(address="bc1qdestination"),
            make_output(address="bc1qdestination"),
        ],
    )

    assert features["unique_input_addresses"] == 1
    assert features["unique_output_addresses"] == 1
