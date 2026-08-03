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

            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                name TEXT NOT NULL,
                average_cycle_length INTEGER NOT NULL DEFAULT 28
                    CHECK (average_cycle_length BETWEEN 15 AND 60),
                average_period_length INTEGER NOT NULL DEFAULT 5
                    CHECK (average_period_length BETWEEN 1 AND 15),
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS accounts (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                email TEXT NOT NULL UNIQUE COLLATE NOCASE,
                password_hash TEXT NOT NULL,
                password_salt TEXT NOT NULL,
                recovery_code_hash TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS sessions (
                token_hash TEXT PRIMARY KEY,
                account_id INTEGER NOT NULL,
                expires_at TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_sessions_expires_at
            ON sessions(expires_at);
            """
        )
        account_columns = {
            row["name"]
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        if "recovery_code_hash" not in account_columns:
            connection.execute(
                "ALTER TABLE accounts ADD COLUMN recovery_code_hash TEXT"
            )
        connection.commit()


def get_connection() -> Iterator[sqlite3.Connection]:
    connection = connect()
    try:
        yield connection
    finally:
        connection.close()
