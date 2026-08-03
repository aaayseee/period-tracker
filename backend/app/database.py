import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional

from .migrations import apply_migrations


DEFAULT_DATABASE_PATH = Path(__file__).resolve().parent.parent / "data" / "period_tracker.db"


def get_database_path() -> Path:
    configured_path = os.getenv("PERIOD_TRACKER_DB")
    return Path(configured_path) if configured_path else DEFAULT_DATABASE_PATH


def connect(path: Optional[Path] = None) -> sqlite3.Connection:
    database_path = path or get_database_path()
    database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def init_database(path: Optional[Path] = None) -> None:
    with connect(path) as connection:
        apply_migrations(connection)


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
