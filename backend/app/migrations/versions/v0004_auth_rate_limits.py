import sqlite3


VERSION = 4
NAME = "auth_rate_limit_events"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE auth_rate_limit_events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bucket_hash TEXT NOT NULL,
            action TEXT NOT NULL,
            occurred_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_auth_rate_limit_bucket_time
        ON auth_rate_limit_events(bucket_hash, occurred_at)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_auth_rate_limit_occurred_at
        ON auth_rate_limit_events(occurred_at)
        """
    )
