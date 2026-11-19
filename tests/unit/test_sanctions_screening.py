from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy.dialects import postgresql

from src.risk.sanctions_screening import screen_bitcoin_address


ADDRESS = "1H939dom7i4WDLCKyGbXUp3fs9CSTNRzgL"


def make_record(**overrides):
    values = {
        "blockchain": "bitcoin",
        "address": ADDRESS,
        "entity_id": "38419",
        "entity_name": "KHATIBI AGHADA, Ahmad",
        "source_record_id": "53723",
        "sanctions_program": "CYBER2",
        "raw_record": {
            "sanctions_programmes": ["CYBER2", "IFSR", "IRGC"],
            "entity_type": "Individual",
            "version_id": "50001",
            "is_primary": True,
            "reliability": "Reported",
        },
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def make_source():
    return SimpleNamespace(
        source_name="OFAC Specially Designated Nationals - Enhanced XML",
        source_url="https://sanctionslistservice.ofac.treas.gov/api/PublicationPreview/exports/SDN_ENHANCED.XML",
        source_key="ofac_sdn_enhanced_2026-11-18",
        dataset_version="2026-11-18T00:00:00-05:00",
        published_at=datetime(2026, 11, 18, 5, 0, tzinfo=timezone.utc),
        checksum_sha256="a" * 64,
        metadata_json={
            "data_as_of": "2026-11-18T00:00:00-05:00"
        },
    )


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.statement = None

    def execute(self, statement):
        self.statement = statement
        return FakeResult(self.rows)


def test_returns_all_records_for_address_with_multiple_entities():
    first = make_record(
        entity_id="38419",
        entity_name="KHATIBI AGHADA, Ahmad",
        source_record_id="53723",
    )
    second = make_record(
        entity_id="38420",
        entity_name="NIKAEEN RAVARI, Amir Hossein",
        source_record_id="53731",
    )
    session = FakeSession([
        (first, make_source()),
        (second, make_source()),
    ])

    result = screen_bitcoin_address(session, ADDRESS)

    assert result["match_status"] == "exact_match"
    assert result["is_sanctioned_address_match"] is True
    assert result["match_count"] == 2
    assert {
        match["entity_id"] for match in result["matches"]
    } == {"38419", "38420"}


def test_preserves_multiple_feature_records_for_same_entity():
    first = make_record(source_record_id="51501")
    second = make_record(source_record_id="51507")
    session = FakeSession([
        (first, make_source()),
        (second, make_source()),
    ])

    result = screen_bitcoin_address(session, ADDRESS)

    assert result["match_count"] == 2
    assert {
        match["source_record_id"] for match in result["matches"]
    } == {"51501", "51507"}


def test_no_match_returns_empty_matches():
    session = FakeSession([])

    result = screen_bitcoin_address(
        session,
        "1BitcoinAddressNotInTheSnapshot",
    )

    assert result["match_status"] == "no_match"
    assert result["is_sanctioned_address_match"] is False
    assert result["match_count"] == 0
    assert result["matches"] == []


def test_address_is_trimmed_but_not_lowercased():
    session = FakeSession([])

    result = screen_bitcoin_address(session, f"  {ADDRESS}  ")

    assert result["address"] == ADDRESS

    compiled = session.statement.compile(
        dialect=postgresql.dialect()
    )
    assert ADDRESS in compiled.params.values()


def test_query_uses_exact_address_equality():
    session = FakeSession([])

    screen_bitcoin_address(session, ADDRESS)

    compiled = session.statement.compile(
        dialect=postgresql.dialect()
    )

    sql = str(compiled)
    assert "sanctioned_crypto_addresses.address =" in sql
    assert compiled.params["address_1"] == ADDRESS


def test_result_includes_source_provenance_and_evidence():
    session = FakeSession([
        (make_record(), make_source())
    ])

    result = screen_bitcoin_address(session, ADDRESS)
    match = result["matches"][0]

    assert match["sanctions_programmes"] == [
        "CYBER2", "IFSR", "IRGC"
    ]
    assert match["reliability"] == "Reported"
    assert match["source"]["source_key"] == (
        "ofac_sdn_enhanced_2026-11-18"
    )
    assert match["source"]["data_as_of"] == (
        "2026-11-18T00:00:00-05:00"
    )
    assert match["source"]["checksum_sha256"] == "a" * 64
    assert result["investigation_note"]


@pytest.mark.parametrize("address", ["", "   ", None, 123])
def test_rejects_invalid_address(address):
    session = FakeSession([])

    with pytest.raises(ValueError):
        screen_bitcoin_address(session, address)
