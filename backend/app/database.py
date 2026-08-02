import os
import sqlite3
from pathlib import Path
from typing import Iterator, Optional


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
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS periods (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                start_date TEXT NOT NULL UNIQUE,
                end_date TEXT,
                flow TEXT NOT NULL DEFAULT 'medium'
                    CHECK (flow IN ('light', 'medium', 'heavy')),
                symptoms TEXT NOT NULL DEFAULT '[]',
                notes TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                CHECK (end_date IS NULL OR end_date >= start_date)
            );

            CREATE INDEX IF NOT EXISTS idx_periods_start_date
            ON periods(start_date DESC);
            """
        )


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()

