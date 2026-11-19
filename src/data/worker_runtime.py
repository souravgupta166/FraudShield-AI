import os
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.engine import Connection, Engine
from sqlalchemy.orm import sessionmaker


WORKER_LOCK_KEY = 73120261119


@dataclass(frozen=True)
class WorkerConfig:
    database_url: str
    poll_interval_seconds: int = 30
    scan_depth: int = 3
    max_pages_per_cycle: int = 5
    page_delay_seconds: float = 1.0

    @classmethod
    def from_env(cls) -> "WorkerConfig":
        database_url = os.getenv("DATABASE_URL")

        if not database_url:
            raise ValueError("DATABASE_URL environment variable is required")

        config = cls(
            database_url=database_url,
            poll_interval_seconds=int(
                os.getenv("BITCOIN_WORKER_POLL_SECONDS", "30")
            ),
            scan_depth=int(
                os.getenv("BITCOIN_WORKER_SCAN_DEPTH", "3")
            ),
            max_pages_per_cycle=int(
                os.getenv("BITCOIN_WORKER_MAX_PAGES_PER_CYCLE", "5")
            ),
            page_delay_seconds=float(
                os.getenv("BITCOIN_WORKER_PAGE_DELAY_SECONDS", "1.0")
            ),
        )

        if config.poll_interval_seconds < 5:
            raise ValueError("Worker poll interval must be at least 5 seconds")

        if not 1 <= config.scan_depth <= 12:
            raise ValueError("Worker scan depth must be between 1 and 12")

        if not 1 <= config.max_pages_per_cycle <= 100:
            raise ValueError("Maximum pages per cycle must be between 1 and 100")

        if not 0 <= config.page_delay_seconds <= 30:
            raise ValueError("Page delay must be between 0 and 30 seconds")

        return config


def create_worker_database(
    database_url: str,
) -> tuple[Engine, sessionmaker]:
    engine = create_engine(
        database_url,
        pool_pre_ping=True,
        pool_size=2,
        max_overflow=1,
    )

    session_factory = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    return engine, session_factory


def try_acquire_worker_lock(
    engine: Engine,
    lock_key: int = WORKER_LOCK_KEY,
) -> Connection | None:
    """Keep this connection open while the worker owns the advisory lock."""
    connection = engine.connect()

    try:
        acquired = connection.execute(
            text("SELECT pg_try_advisory_lock(:lock_key)"),
            {"lock_key": lock_key},
        ).scalar_one()

        connection.commit()

        if not acquired:
            connection.close()
            return None

        return connection

    except Exception:
        connection.close()
        raise


def release_worker_lock(
    connection: Connection,
    lock_key: int = WORKER_LOCK_KEY,
) -> None:
    try:
        connection.execute(
            text("SELECT pg_advisory_unlock(:lock_key)"),
            {"lock_key": lock_key},
        )
        connection.commit()
    finally:
        connection.close()
