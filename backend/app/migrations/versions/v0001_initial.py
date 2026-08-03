import sqlite3


VERSION = 1
NAME = "initial_schema"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
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
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_periods_start_date ON periods(start_date DESC)"
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS profile (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            name TEXT NOT NULL,
            average_cycle_length INTEGER NOT NULL DEFAULT 28
                CHECK (average_cycle_length BETWEEN 15 AND 60),
            average_period_length INTEGER NOT NULL DEFAULT 5
                CHECK (average_period_length BETWEEN 1 AND 15),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS accounts (
            id INTEGER PRIMARY KEY CHECK (id = 1),
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS sessions (
            token_hash TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_sessions_expires_at ON sessions(expires_at)"
    )

    required_columns = {
        "periods": {
            "id",
            "start_date",
            "end_date",
            "flow",
            "symptoms",
            "notes",
            "created_at",
            "updated_at",
        },
        "profile": {
            "id",
            "name",
            "average_cycle_length",
            "average_period_length",
            "created_at",
            "updated_at",
        },
        "accounts": {
            "id",
            "email",
            "password_hash",
            "password_salt",
            "created_at",
            "updated_at",
        },
        "sessions": {
            "token_hash",
            "account_id",
            "expires_at",
            "created_at",
        },
    }
    for table, expected in required_columns.items():
        actual = {
            row["name"]
            for row in connection.execute(f"PRAGMA table_info({table})").fetchall()
        }
        missing = expected - actual
        if missing:
            missing_list = ", ".join(sorted(missing))
            raise RuntimeError(
                f"Existing {table} table is incompatible; missing columns: {missing_list}."
            )
