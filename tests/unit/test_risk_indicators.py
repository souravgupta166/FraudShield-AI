import pytest

from src.risk.risk_indicators import (
    RiskThresholds,
    evaluate_transaction_indicators,
)


@pytest.fixture
def thresholds():
    return RiskThresholds(
        high_input_count=10,
        high_output_count=10,
    )


@pytest.fixture
def normal_features():
    return {
        "txid": "a" * 64,
        "input_count": 2,
        "output_count": 2,
        "input_values_complete": True,
        "fee_reconciliation_valid": True,
        "input_value_sats": 100000,
        "output_value_sats": 99000,
        "fee_sats": 1000,
    }


def test_normal_transaction_has_no_findings(
    normal_features,
    thresholds,
):
    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert findings == []


def test_large_input_consolidation_is_detected(
    normal_features,
    thresholds,
):
    normal_features["input_count"] = 12

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert len(findings) == 1
    assert findings[0]["indicator_code"] == (
        "large_input_consolidation"
    )
    assert findings[0]["evidence"]["input_count"] == 12


def test_high_output_count_is_detected(
    normal_features,
    thresholds,
):
    normal_features["output_count"] = 15

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert len(findings) == 1
    assert findings[0]["indicator_code"] == "high_output_count"


def test_fee_mismatch_is_a_data_integrity_warning(
    normal_features,
    thresholds,
):
    normal_features["fee_reconciliation_valid"] = False

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert len(findings) == 1
    assert findings[0]["indicator_code"] == (
        "fee_reconciliation_mismatch"
    )
    assert findings[0]["category"] == "data_integrity"
    assert findings[0]["severity"] == "warning"


def test_incomplete_input_values_are_reported(
    normal_features,
    thresholds,
):
    normal_features["input_values_complete"] = False
    normal_features["input_value_sats"] = None
    normal_features["fee_reconciliation_valid"] = None

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert len(findings) == 1
    assert findings[0]["indicator_code"] == (
        "incomplete_input_value_data"
    )


def test_multiple_indicators_can_be_returned(
    normal_features,
    thresholds,
):
    normal_features["input_count"] = 12
    normal_features["output_count"] = 15

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    codes = {finding["indicator_code"] for finding in findings}

    assert codes == {
        "large_input_consolidation",
        "high_output_count",
    }


def test_thresholds_must_be_at_least_two():
    with pytest.raises(ValueError):
        RiskThresholds(
            high_input_count=1,
            high_output_count=10,
        )


def test_missing_fee_reconciliation_is_not_flagged(
    normal_features,
    thresholds,
):
    normal_features["fee_reconciliation_valid"] = None

    findings = evaluate_transaction_indicators(
        normal_features,
        thresholds,
    )

    assert not any(
        finding["indicator_code"] == "fee_reconciliation_mismatch"
        for finding in findings
    )
