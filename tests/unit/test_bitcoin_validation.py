import pytest

from src.data.bitcoin_validation import validate_transaction_accounting


def test_valid_normal_transaction():
    transaction = {
        "fee": 13034,
        "vin": [
            {"prevout": {"value": 859485}}
        ],
        "vout": [
            {"value": 284007},
            {"value": 562444},
        ],
    }

    result = validate_transaction_accounting(transaction)

    assert result["is_coinbase"] is False
    assert result["input_total_sats"] == 859485
    assert result["output_total_sats"] == 846451
    assert result["calculated_fee_sats"] == 13034
    assert result["accounting_valid"] is True


def test_detect_fee_mismatch():
    transaction = {
        "fee": 10000,
        "vin": [{"prevout": {"value": 859485}}],
        "vout": [{"value": 846451}],
    }

    with pytest.raises(ValueError, match="Fee mismatch"):
        validate_transaction_accounting(transaction)


def test_coinbase_transaction_is_handled_separately():
    transaction = {
        "fee": 0,
        "vin": [{"is_coinbase": True}],
        "vout": [{"value": 5000000000}],
    }

    result = validate_transaction_accounting(transaction)

    assert result["is_coinbase"] is True
    assert result["input_total_sats"] is None
    assert result["calculated_fee_sats"] is None
    assert result["accounting_valid"] is None


def test_reject_missing_previous_output():
    transaction = {
        "fee": 0,
        "vin": [{"txid": "example"}],
        "vout": [{"value": 1000}],
    }

    with pytest.raises(ValueError, match="missing previous output"):
        validate_transaction_accounting(transaction)


def test_reject_negative_output_value():
    transaction = {
        "fee": 0,
        "vin": [{"prevout": {"value": 1000}}],
        "vout": [{"value": -100}],
    }

    with pytest.raises(ValueError, match="non-negative integer"):
        validate_transaction_accounting(transaction)


def test_reject_outputs_exceeding_inputs():
    transaction = {
        "fee": 0,
        "vin": [{"prevout": {"value": 1000}}],
        "vout": [{"value": 1200}],
    }

    with pytest.raises(ValueError, match="Outputs exceed"):
        validate_transaction_accounting(transaction)
