from types import SimpleNamespace

import pytest

from src.data import bitcoin_block_processor as processor


BLOCK_HASH = "a" * 64
OTHER_BLOCK_HASH = "b" * 64
TXID_1 = "1" * 64
TXID_2 = "2" * 64


def make_transaction(txid, block_hash=BLOCK_HASH):
    return SimpleNamespace(
        txid=txid,
        status={
            "confirmed": True,
            "block_hash": block_hash,
        },
    )


class FakeClient:
    def __init__(
        self,
        txids=None,
        transactions=None,
        canonical_hash=BLOCK_HASH,
        in_best_chain=True,
    ):
        self.txids = txids if txids is not None else [TXID_1]
        self.transactions = (
            transactions
            if transactions is not None
            else [make_transaction(txid) for txid in self.txids]
        )
        self.canonical_hash = canonical_hash
        self.in_best_chain = in_best_chain
        self.calls = []

    def get_block_hash_at_height(self, height):
        self.calls.append(("canonical_hash", height))
        return self.canonical_hash

    def get_block_status(self, block_hash):
        self.calls.append(("block_status", block_hash))
        return {"in_best_chain": self.in_best_chain}

    def get_block_txids(self, block_hash):
        self.calls.append(("txids", block_hash))
        return self.txids

    def get_block_transactions(self, block_hash, start_index):
        self.calls.append(("transactions", block_hash, start_index))
        return self.transactions[start_index:]

    def get_block(self, block_hash):
        self.calls.append(("block", block_hash))
        return {
            "id": block_hash,
            "height": 976434,
        }


class FakeSession:
    def __init__(self, block, stored_count=1):
        self.block = block
        self.stored_count = stored_count
        self.executed = []
        self.transaction = self

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        return False

    def begin(self):
        return self

    def get(self, model, key):
        return self.block if key == BLOCK_HASH else None

    def scalar(self, statement):
        return self.stored_count

    def execute(self, statement):
        self.executed.append(statement)


class FakeSessionFactory:
    def __init__(self, block, stored_count=1):
        self.session = FakeSession(block, stored_count)

    def __call__(self):
        return self.session


def make_block(
    tx_count=1,
    cursor=0,
    canonical=True,
):
    return SimpleNamespace(
        block_hash=BLOCK_HASH,
        height=976434,
        tx_count=tx_count,
        next_transaction_index=cursor,
        ingested_transaction_count=0,
        is_canonical=canonical,
        ingestion_status="partial",
        last_ingested_at=None,
        ingestion_error=None,
    )


def test_processes_page_and_advances_cursor(monkeypatch):
    block = make_block(tx_count=1)
    session_factory = FakeSessionFactory(block, stored_count=1)
    client = FakeClient()
    ingested = []

    monkeypatch.setattr(
        processor,
        "ingest_confirmed_transaction",
        lambda **kwargs: ingested.append(kwargs["transaction"].txid),
    )

    result = processor.process_block_page(
        session_factory,
        client,
        BLOCK_HASH,
    )

    assert ingested == [TXID_1]
    assert result["transactions_processed"] == 1
    assert result["next_transaction_index"] == 1
    assert result["ingested_transaction_count"] == 1
    assert result["status"] == "completed"
    assert block.next_transaction_index == 1
    assert block.ingestion_status == "completed"


def test_rejects_transaction_page_with_wrong_order(monkeypatch):
    block = make_block(tx_count=2)
    session_factory = FakeSessionFactory(block)
    client = FakeClient(
        txids=[TXID_1, TXID_2],
        transactions=[
            make_transaction(TXID_2),
            make_transaction(TXID_1),
        ],
    )

    monkeypatch.setattr(
        processor,
        "ingest_confirmed_transaction",
        lambda **kwargs: pytest.fail("Unexpected ingestion"),
    )

    with pytest.raises(ValueError, match="ordered block transaction IDs"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert block.next_transaction_index == 0


def test_rejects_transaction_from_another_block(monkeypatch):
    block = make_block(tx_count=1)
    session_factory = FakeSessionFactory(block)
    client = FakeClient(
        transactions=[make_transaction(TXID_1, OTHER_BLOCK_HASH)]
    )

    monkeypatch.setattr(
        processor,
        "ingest_confirmed_transaction",
        lambda **kwargs: pytest.fail("Unexpected ingestion"),
    )

    with pytest.raises(ValueError, match="does not belong"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert block.next_transaction_index == 0


def test_ingestion_failure_does_not_advance_cursor(monkeypatch):
    block = make_block(tx_count=2)
    session_factory = FakeSessionFactory(block)
    client = FakeClient(
        txids=[TXID_1, TXID_2],
        transactions=[
            make_transaction(TXID_1),
            make_transaction(TXID_2),
        ],
    )

    ingested = []

    def fake_ingestion(**kwargs):
        txid = kwargs["transaction"].txid
        ingested.append(txid)

        if txid == TXID_2:
            raise RuntimeError("Simulated ingestion failure")

    monkeypatch.setattr(
        processor,
        "ingest_confirmed_transaction",
        fake_ingestion,
    )

    with pytest.raises(RuntimeError, match="Simulated ingestion failure"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert ingested == [TXID_1, TXID_2]
    assert block.next_transaction_index == 0
    assert block.ingestion_status == "partial"


def test_rejects_non_canonical_block():
    block = make_block(canonical=False)
    session_factory = FakeSessionFactory(block)
    client = FakeClient()

    with pytest.raises(ValueError, match="non-canonical"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert client.calls == []


def test_detects_reorganisation_before_processing():
    block = make_block()
    session_factory = FakeSessionFactory(block)
    client = FakeClient(canonical_hash=OTHER_BLOCK_HASH)

    with pytest.raises(ValueError, match="reorganisation detected"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert block.next_transaction_index == 0
    assert not any(call[0] == "txids" for call in client.calls)


def test_marks_block_completed_when_cursor_is_at_end():
    block = make_block(tx_count=1, cursor=1)
    session_factory = FakeSessionFactory(block)
    client = FakeClient()

    result = processor.process_block_page(
        session_factory,
        client,
        BLOCK_HASH,
    )

    assert result["transactions_processed"] == 0
    assert result["next_transaction_index"] == 1
    assert result["status"] == "completed"
    assert len(session_factory.session.executed) == 1
    assert not any(call[0] == "transactions" for call in client.calls)


def test_rejects_block_transaction_count_mismatch():
    block = make_block(tx_count=2)
    session_factory = FakeSessionFactory(block)
    client = FakeClient(txids=[TXID_1])

    with pytest.raises(ValueError, match="does not match its metadata"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert block.next_transaction_index == 0


def test_rejects_duplicate_transaction_ids():
    block = make_block(tx_count=2)
    session_factory = FakeSessionFactory(block)
    client = FakeClient(txids=[TXID_1, TXID_1])

    with pytest.raises(ValueError, match="duplicate IDs"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert block.next_transaction_index == 0


def test_rejects_unknown_block():
    session_factory = FakeSessionFactory(None)
    client = FakeClient()

    with pytest.raises(ValueError, match="Unknown block"):
        processor.process_block_page(
            session_factory,
            client,
            BLOCK_HASH,
        )

    assert client.calls == []
