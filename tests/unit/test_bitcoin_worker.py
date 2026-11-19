import threading
from types import SimpleNamespace

import pytest

from src.data import bitcoin_worker as worker
from src.data.worker_runtime import WorkerConfig


BLOCK_1 = "1" * 64
BLOCK_2 = "2" * 64
BLOCK_3 = "3" * 64


@pytest.fixture
def config():
    return WorkerConfig(
        database_url="postgresql://test:test@localhost/test",
        poll_interval_seconds=5,
        scan_depth=3,
        max_pages_per_cycle=2,
        page_delay_seconds=0,
    )


def test_cycle_processes_blocks_in_round_robin_order_and_respects_page_limit(
    monkeypatch,
    config,
):
    discovered = [
        {"height": 100, "block_hash": BLOCK_1},
        {"height": 101, "block_hash": BLOCK_2},
        {"height": 102, "block_hash": BLOCK_3},
    ]
    processed = []

    monkeypatch.setattr(
        worker,
        "discover_recent_canonical_blocks",
        lambda **kwargs: discovered,
    )

    def fake_process(session_factory, client, block_hash):
        processed.append(block_hash)
        return {
            "height": 102,
            "transactions_processed": 25,
            "next_transaction_index": 25,
            "status": "partial",
        }

    monkeypatch.setattr(worker, "process_block_page", fake_process)

    from dataclasses import replace

    cycle_config = replace(config, max_pages_per_cycle=5)

    result = worker.run_ingestion_cycle(
        session_factory=object(),
        client=object(),
        config=cycle_config,
        stop_event=threading.Event(),
    )

    assert processed == [BLOCK_3, BLOCK_2, BLOCK_1, BLOCK_3, BLOCK_2]
    assert result == {
        "blocks_discovered": 3,
        "pages_processed": 5,
        "transactions_processed": 125,
        "failed_blocks": 0,
    }


def test_cycle_moves_to_older_block_when_newer_block_completes(
    monkeypatch,
    config,
):
    discovered = [
        {"height": 100, "block_hash": BLOCK_1},
        {"height": 101, "block_hash": BLOCK_2},
        {"height": 102, "block_hash": BLOCK_3},
    ]
    processed = []

    monkeypatch.setattr(
        worker,
        "discover_recent_canonical_blocks",
        lambda **kwargs: discovered,
    )

    def fake_process(session_factory, client, block_hash):
        processed.append(block_hash)
        return {
            "height": 102,
            "transactions_processed": 10,
            "next_transaction_index": 10,
            "status": "completed",
        }

    monkeypatch.setattr(worker, "process_block_page", fake_process)

    result = worker.run_ingestion_cycle(
        session_factory=object(),
        client=object(),
        config=config,
        stop_event=threading.Event(),
    )

    assert processed == [BLOCK_3, BLOCK_2]
    assert result["pages_processed"] == 2
    assert result["transactions_processed"] == 20


def test_cycle_records_failed_block_and_continues(
    monkeypatch,
    config,
):
    discovered = [
        {"height": 101, "block_hash": BLOCK_2},
        {"height": 102, "block_hash": BLOCK_3},
    ]
    processed = []
    failures = []

    monkeypatch.setattr(
        worker,
        "discover_recent_canonical_blocks",
        lambda **kwargs: discovered,
    )

    def fake_process(session_factory, client, block_hash):
        processed.append(block_hash)
        if block_hash == BLOCK_3:
            raise RuntimeError("Temporary API failure")

        return {
            "height": 101,
            "transactions_processed": 25,
            "next_transaction_index": 25,
            "status": "completed",
        }

    monkeypatch.setattr(worker, "process_block_page", fake_process)
    monkeypatch.setattr(
        worker,
        "mark_block_failed",
        lambda session_factory, block_hash, error: failures.append(
            (block_hash, str(error))
        ),
    )

    result = worker.run_ingestion_cycle(
        session_factory=object(),
        client=object(),
        config=config,
        stop_event=threading.Event(),
    )

    assert processed == [BLOCK_3, BLOCK_2]
    assert failures == [(BLOCK_3, "Temporary API failure")]
    assert result["failed_blocks"] == 1
    assert result["pages_processed"] == 1
    assert result["transactions_processed"] == 25


def test_cycle_stops_when_shutdown_is_requested(
    monkeypatch,
    config,
):
    stop_event = threading.Event()
    discovered = [
        {"height": 101, "block_hash": BLOCK_2},
        {"height": 102, "block_hash": BLOCK_3},
    ]
    processed = []

    monkeypatch.setattr(
        worker,
        "discover_recent_canonical_blocks",
        lambda **kwargs: discovered,
    )

    def fake_process(session_factory, client, block_hash):
        processed.append(block_hash)
        stop_event.set()
        return {
            "height": 102,
            "transactions_processed": 25,
            "next_transaction_index": 25,
            "status": "partial",
        }

    monkeypatch.setattr(worker, "process_block_page", fake_process)

    result = worker.run_ingestion_cycle(
        session_factory=object(),
        client=object(),
        config=config,
        stop_event=stop_event,
    )

    assert processed == [BLOCK_3]
    assert result["pages_processed"] == 1


def test_mark_block_failed_records_error_without_cursor_change(monkeypatch):
    block = SimpleNamespace(
        next_transaction_index=25,
        ingestion_status="partial",
        ingestion_error=None,
        is_canonical=True,
    )

    class FakeSession:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def begin(self):
            return self

        def execute(self, statement):
            return None

    monkeypatch.setattr(
        worker,
        "update",
        lambda model: SimpleNamespace(
            where=lambda *args: SimpleNamespace(
                values=lambda **kwargs: kwargs
            )
        ),
    )

    worker.mark_block_failed(
        lambda: FakeSession(),
        BLOCK_1,
        RuntimeError("Simulated failure"),
    )

    assert block.next_transaction_index == 25


def test_worker_releases_lock_and_disposes_engine(
    monkeypatch,
    config,
):
    calls = []

    class FakeEngine:
        def dispose(self):
            calls.append("engine_disposed")

    class FakeClient:
        def __enter__(self):
            calls.append("client_entered")
            return self

        def __exit__(self, *args):
            calls.append("client_closed")

    lock = object()

    monkeypatch.setattr(
        worker,
        "create_worker_database",
        lambda database_url: (FakeEngine(), object()),
    )
    monkeypatch.setattr(
        worker,
        "try_acquire_worker_lock",
        lambda engine: lock,
    )
    monkeypatch.setattr(
        worker,
        "release_worker_lock",
        lambda connection: calls.append("lock_released"),
    )
    monkeypatch.setattr(
        worker,
        "run_ingestion_cycle",
        lambda **kwargs: kwargs["stop_event"].set(),
    )

    worker.run_worker(config, threading.Event(), FakeClient)

    assert calls == [
        "client_entered",
        "client_closed",
        "lock_released",
        "engine_disposed",
    ]


def test_worker_does_not_start_client_without_lock(
    monkeypatch,
    config,
):
    calls = []

    class FakeEngine:
        def dispose(self):
            calls.append("engine_disposed")

    class FakeClient:
        def __init__(self):
            calls.append("client_created")

    stop_event = threading.Event()

    def no_lock(engine):
        stop_event.set()
        return None

    monkeypatch.setattr(
        worker,
        "create_worker_database",
        lambda database_url: (FakeEngine(), object()),
    )
    monkeypatch.setattr(worker, "try_acquire_worker_lock", no_lock)

    worker.run_worker(config, stop_event, FakeClient)

    assert calls == ["engine_disposed"]
