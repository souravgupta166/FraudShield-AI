import pytest

from src.data.bitcoin_ingestion import _resolve_block_metadata


BLOCK_HASH = "a" * 64

VALID_BLOCK = {
    "id": BLOCK_HASH,
    "timestamp": 1760000000,
    "height": 976434,
    "tx_count": 2340,
}


class FakeClient:
    def __init__(self, block_data=None):
        self.block_data = block_data
        self.calls = []

    def get_block(self, block_hash):
        self.calls.append(block_hash)
        return self.block_data


def test_supplied_metadata_is_reused_without_api_request():
    client = FakeClient()

    result = _resolve_block_metadata(BLOCK_HASH, client, VALID_BLOCK)

    assert result[0] == VALID_BLOCK
    assert result[2:] == (976434, 2340)
    assert result[1].timestamp() == 1760000000
    assert client.calls == []


def test_metadata_is_fetched_when_not_supplied():
    client = FakeClient(VALID_BLOCK)

    result = _resolve_block_metadata(BLOCK_HASH, client)

    assert result[0] == VALID_BLOCK
    assert client.calls == [BLOCK_HASH]


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("id", "b" * 64, "hash does not match"),
        ("id", None, "hash does not match"),
        ("timestamp", True, "invalid timestamp"),
        ("timestamp", "1760000000", "invalid timestamp"),
        ("height", -1, "invalid height"),
        ("height", True, "invalid height"),
        ("tx_count", -1, "invalid transaction count"),
        ("tx_count", True, "invalid transaction count"),
    ],
)
def test_invalid_block_metadata_is_rejected(field, value, message):
    block_data = {**VALID_BLOCK, field: value}
    client = FakeClient()

    with pytest.raises(ValueError, match=message):
        _resolve_block_metadata(BLOCK_HASH, client, block_data)


def test_non_dictionary_metadata_is_rejected():
    with pytest.raises(ValueError, match="must be a dictionary"):
        _resolve_block_metadata(BLOCK_HASH, FakeClient(), [])


def test_block_upsert_preserves_existing_canonical_status():
    from sqlalchemy.dialects import postgresql

    from src.data.bitcoin_ingestion import _build_block_upsert_statement

    from datetime import datetime, timezone

    statement = _build_block_upsert_statement(
        block_hash=BLOCK_HASH,
        block_height=976434,
        block_data=VALID_BLOCK,
        block_time=datetime.fromtimestamp(1760000000, tz=timezone.utc),
        tx_count=2340,
    )

    sql = str(statement.compile(dialect=postgresql.dialect()))
    insert_clause, update_clause = sql.split("DO UPDATE SET", maxsplit=1)

    assert "is_canonical" in insert_clause
    assert "is_canonical" not in update_clause
