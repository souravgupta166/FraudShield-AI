import pytest

from src.data.worker_runtime import (
    WORKER_LOCK_KEY,
    WorkerConfig,
    try_acquire_worker_lock,
    release_worker_lock,
)


def test_worker_config_uses_defaults(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test")

    for name in (
        "BITCOIN_WORKER_POLL_SECONDS",
        "BITCOIN_WORKER_SCAN_DEPTH",
        "BITCOIN_WORKER_MAX_PAGES_PER_CYCLE",
        "BITCOIN_WORKER_PAGE_DELAY_SECONDS",
    ):
        monkeypatch.delenv(name, raising=False)

    config = WorkerConfig.from_env()

    assert config.database_url == "postgresql+psycopg://test"
    assert config.poll_interval_seconds == 30
    assert config.scan_depth == 3
    assert config.max_pages_per_cycle == 5
    assert config.page_delay_seconds == 1.0


def test_worker_config_reads_environment(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test")
    monkeypatch.setenv("BITCOIN_WORKER_POLL_SECONDS", "45")
    monkeypatch.setenv("BITCOIN_WORKER_SCAN_DEPTH", "4")
    monkeypatch.setenv("BITCOIN_WORKER_MAX_PAGES_PER_CYCLE", "8")
    monkeypatch.setenv("BITCOIN_WORKER_PAGE_DELAY_SECONDS", "1.5")

    config = WorkerConfig.from_env()

    assert config.poll_interval_seconds == 45
    assert config.scan_depth == 4
    assert config.max_pages_per_cycle == 8
    assert config.page_delay_seconds == 1.5


def test_worker_config_requires_database_url(monkeypatch):
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValueError, match="DATABASE_URL"):
        WorkerConfig.from_env()


@pytest.mark.parametrize(
    ("variable", "value", "message"),
    [
        ("BITCOIN_WORKER_POLL_SECONDS", "4", "poll interval"),
        ("BITCOIN_WORKER_SCAN_DEPTH", "0", "scan depth"),
        ("BITCOIN_WORKER_SCAN_DEPTH", "13", "scan depth"),
        ("BITCOIN_WORKER_MAX_PAGES_PER_CYCLE", "0", "Maximum pages"),
        ("BITCOIN_WORKER_MAX_PAGES_PER_CYCLE", "101", "Maximum pages"),
        ("BITCOIN_WORKER_PAGE_DELAY_SECONDS", "-1", "Page delay"),
        ("BITCOIN_WORKER_PAGE_DELAY_SECONDS", "31", "Page delay"),
    ],
)
def test_worker_config_rejects_invalid_settings(
    monkeypatch, variable, value, message
):
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://test")
    monkeypatch.setenv(variable, value)

    with pytest.raises(ValueError, match=message):
        WorkerConfig.from_env()


def test_worker_lock_returns_connection_when_acquired(monkeypatch):
    class FakeResult:
        def scalar_one(self):
            return True

    class FakeConnection:
        def __init__(self):
            self.committed = False
            self.closed = False
            self.statement = None
            self.parameters = None

        def execute(self, statement, parameters):
            self.statement = str(statement)
            self.parameters = parameters
            return FakeResult()

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    class FakeEngine:
        def __init__(self):
            self.connection = FakeConnection()

        def connect(self):
            return self.connection

    engine = FakeEngine()
    connection = try_acquire_worker_lock(engine)

    assert connection is engine.connection
    assert connection.committed is True
    assert connection.closed is False
    assert "pg_try_advisory_lock" in connection.statement
    assert connection.parameters == {"lock_key": WORKER_LOCK_KEY}


def test_worker_lock_closes_connection_when_already_held():
    class FakeResult:
        def scalar_one(self):
            return False

    class FakeConnection:
        closed = False

        def execute(self, statement, parameters):
            return FakeResult()

        def commit(self):
            pass

        def close(self):
            self.closed = True

    class FakeEngine:
        def __init__(self):
            self.connection = FakeConnection()

        def connect(self):
            return self.connection

    engine = FakeEngine()

    result = try_acquire_worker_lock(engine)

    assert result is None
    assert engine.connection.closed is True


def test_worker_lock_closes_connection_on_database_error():
    class FakeConnection:
        closed = False

        def execute(self, statement, parameters):
            raise RuntimeError("database unavailable")

        def close(self):
            self.closed = True

    class FakeEngine:
        def __init__(self):
            self.connection = FakeConnection()

        def connect(self):
            return self.connection

    engine = FakeEngine()

    with pytest.raises(RuntimeError, match="database unavailable"):
        try_acquire_worker_lock(engine)

    assert engine.connection.closed is True


def test_release_worker_lock_unlocks_and_closes_connection():
    class FakeConnection:
        def __init__(self):
            self.statement = None
            self.parameters = None
            self.committed = False
            self.closed = False

        def execute(self, statement, parameters):
            self.statement = str(statement)
            self.parameters = parameters

        def commit(self):
            self.committed = True

        def close(self):
            self.closed = True

    connection = FakeConnection()

    release_worker_lock(connection)

    assert "pg_advisory_unlock" in connection.statement
    assert connection.parameters == {"lock_key": WORKER_LOCK_KEY}
    assert connection.committed is True
    assert connection.closed is True
