from types import SimpleNamespace

import pytest

from src.data.bitcoin_block_discovery import (
    discover_recent_canonical_blocks,
)


BLOCK_HASH = "a" * 64

VALID_BLOCK = {
    "id": BLOCK_HASH,
    "timestamp": 1760000000,
    "height": 976434,
    "tx_count": 2340,
    "previousblockhash": "b" * 64,
}


class FakeClient:
    def __init__(
        self,
        tip_height=976434,
        block_hash=BLOCK_HASH,
        block_data=None,
        block_status=None,
    ):
        self.tip_height = tip_height
        self.block_hash = block_hash
        self.block_data = block_data or VALID_BLOCK
        self.block_status = block_status or {"in_best_chain": True}
        self.calls = []

    def get_tip_height(self):
        self.calls.append(("tip",))
        return self.tip_height

    def get_block_hash_at_height(self, height):
        self.calls.append(("hash", height))
        return self.block_hash

    def get_block(self, block_hash):
        self.calls.append(("block", block_hash))
        return self.block_data

    def get_block_status(self, block_hash):
        self.calls.append(("status", block_hash))
        return self.block_status


class FakeSession:
    def __init__(self, previous_blocks=None):
        self.previous_blocks = previous_blocks or []
        self.executed = []
        self.transaction = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def begin(self):
        return self

    def scalars(self, statement):
        self.select_statement = statement
        return FakeScalarResult(self.previous_blocks)

    def execute(self, statement):
        self.executed.append(statement)


class FakeScalarResult:
    def __init__(self, items):
        self.items = items

    def all(self):
        return self.items

    def execute(self, statement):
        self.executed.append(statement)


class FakeSessionFactory:
    def __init__(self, previous_blocks=None):
        self.sessions = []
        self.previous_blocks = previous_blocks or []

    def __call__(self):
        session = FakeSession(self.previous_blocks)
        self.sessions.append(session)
        return session


def test_discovers_and_persists_verified_canonical_block():
    client = FakeClient()
    session_factory = FakeSessionFactory()

    result = discover_recent_canonical_blocks(
        session_factory,
        client,
        scan_depth=1,
    )

    assert result == [
        {
            "height": 976434,
            "block_hash": BLOCK_HASH,
            "tx_count": 2340,
            "is_canonical": True,
            "replaced_block_hashes": [],
        }
    ]

    assert len(session_factory.sessions) == 1
    assert len(session_factory.sessions[0].executed) == 3
    assert client.calls == [
        ("tip",),
        ("hash", 976434),
        ("block", BLOCK_HASH),
        ("status", BLOCK_HASH),
    ]


def test_reorganisation_marks_previous_block_and_transactions():
    previous_hash = "c" * 64
    previous_block = SimpleNamespace(block_hash=previous_hash)

    client = FakeClient()
    session_factory = FakeSessionFactory([previous_block])

    result = discover_recent_canonical_blocks(
        session_factory,
        client,
        scan_depth=1,
    )

    assert result[0]["replaced_block_hashes"] == [previous_hash]

    statements = session_factory.sessions[0].executed
    assert len(statements) == 5


@pytest.mark.parametrize("scan_depth", [0, 13, True, 1.5])
def test_rejects_invalid_scan_depth(scan_depth):
    with pytest.raises(ValueError, match="Scan depth"):
        discover_recent_canonical_blocks(
            FakeSessionFactory(),
            FakeClient(),
            scan_depth=scan_depth,
        )


@pytest.mark.parametrize("tip_height", [-1, True, "976434"])
def test_rejects_invalid_tip_height(tip_height):
    client = FakeClient(tip_height=tip_height)
    session_factory = FakeSessionFactory()

    with pytest.raises(ValueError, match="tip height"):
        discover_recent_canonical_blocks(
            session_factory,
            client,
            scan_depth=1,
        )

    assert session_factory.sessions == []


def test_rejects_metadata_height_mismatch():
    block_data = {**VALID_BLOCK, "height": 976433}
    client = FakeClient(block_data=block_data)
    session_factory = FakeSessionFactory()

    with pytest.raises(ValueError, match="height mismatch"):
        discover_recent_canonical_blocks(
            session_factory,
            client,
            scan_depth=1,
        )

    assert session_factory.sessions == []


def test_rejects_block_not_in_best_chain():
    client = FakeClient(block_status={"in_best_chain": False})
    session_factory = FakeSessionFactory()

    with pytest.raises(ValueError, match="not in the best chain"):
        discover_recent_canonical_blocks(
            session_factory,
            client,
            scan_depth=1,
        )

    assert session_factory.sessions == []


def test_rejects_invalid_block_status():
    client = FakeClient(block_status={"in_best_chain": "true"})
    session_factory = FakeSessionFactory()

    with pytest.raises(ValueError, match="in_best_chain"):
        discover_recent_canonical_blocks(
            session_factory,
            client,
            scan_depth=1,
        )

    assert session_factory.sessions == []
