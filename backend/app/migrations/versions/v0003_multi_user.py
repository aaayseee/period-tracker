import sqlite3


VERSION = 3
NAME = "multi_user_accounts_and_invites"


def upgrade(connection: sqlite3.Connection) -> None:
    account_rows = connection.execute("SELECT COUNT(*) FROM accounts").fetchone()[0]
    profile_rows = connection.execute("SELECT COUNT(*) FROM profile").fetchone()[0]
    period_rows = connection.execute("SELECT COUNT(*) FROM periods").fetchone()[0]
    if account_rows == 0 and (profile_rows or period_rows):
        raise RuntimeError(
            "Health data exists without an account; multi-user migration cannot assign ownership safely."
        )

    connection.execute(
        """
        CREATE TABLE accounts_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE COLLATE NOCASE,
            password_hash TEXT NOT NULL,
            password_salt TEXT NOT NULL,
            recovery_code_hash TEXT,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK (role IN ('admin', 'user')),
            is_active INTEGER NOT NULL DEFAULT 1
                CHECK (is_active IN (0, 1)),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.execute(
        """
        INSERT INTO accounts_new (
            id, email, password_hash, password_salt, recovery_code_hash,
            role, is_active, created_at, updated_at
        )
        SELECT id, email, password_hash, password_salt, recovery_code_hash,
               'user', 1, created_at, updated_at
        FROM accounts
        """
    )

    connection.execute(
        """
        CREATE TABLE profile_new (
            account_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            average_cycle_length INTEGER NOT NULL DEFAULT 28
                CHECK (average_cycle_length BETWEEN 15 AND 60),
            average_period_length INTEGER NOT NULL DEFAULT 5
                CHECK (average_period_length BETWEEN 1 AND 15),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts_new(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO profile_new (
            account_id, name, average_cycle_length, average_period_length,
            created_at, updated_at
        )
        SELECT id, name, average_cycle_length, average_period_length,
               created_at, updated_at
        FROM profile
        """
    )

    connection.execute(
        """
        CREATE TABLE periods_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT,
            flow TEXT NOT NULL DEFAULT 'medium'
                CHECK (flow IN ('light', 'medium', 'heavy')),
            symptoms TEXT NOT NULL DEFAULT '[]',
            notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts_new(id) ON DELETE CASCADE,
            UNIQUE (account_id, start_date),
            CHECK (end_date IS NULL OR end_date >= start_date)
        )
        """
    )
    if period_rows:
        owner_id = connection.execute("SELECT id FROM accounts LIMIT 1").fetchone()[0]
        connection.execute(
            """
            INSERT INTO periods_new (
                id, account_id, start_date, end_date, flow, symptoms, notes,
                created_at, updated_at
            )
            SELECT id, ?, start_date, end_date, flow, symptoms, notes,
                   created_at, updated_at
            FROM periods
            """,
            (owner_id,),
        )

    connection.execute(
        """
        CREATE TABLE sessions_new (
            token_hash TEXT PRIMARY KEY,
            account_id INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts_new(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        INSERT INTO sessions_new (token_hash, account_id, expires_at, created_at)
        SELECT token_hash, account_id, expires_at, created_at FROM sessions
        """
    )

    connection.execute(
        """
        CREATE TABLE invite_codes_new (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code_hash TEXT NOT NULL UNIQUE,
            created_by INTEGER NOT NULL,
            expires_at TEXT NOT NULL,
            max_uses INTEGER NOT NULL DEFAULT 1 CHECK (max_uses BETWEEN 1 AND 100),
            use_count INTEGER NOT NULL DEFAULT 0 CHECK (use_count >= 0),
            revoked_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES accounts_new(id) ON DELETE CASCADE
        )
        """
    )

    connection.execute("DROP TABLE sessions")
    connection.execute("DROP TABLE periods")
    connection.execute("DROP TABLE profile")
    connection.execute("DROP TABLE accounts")
    connection.execute("ALTER TABLE accounts_new RENAME TO accounts")
    connection.execute("ALTER TABLE profile_new RENAME TO profile")
    connection.execute("ALTER TABLE periods_new RENAME TO periods")
    connection.execute("ALTER TABLE sessions_new RENAME TO sessions")
    connection.execute("ALTER TABLE invite_codes_new RENAME TO invite_codes")

    connection.execute(
        "CREATE INDEX idx_periods_account_start ON periods(account_id, start_date DESC)"
    )
    connection.execute(
        "CREATE INDEX idx_sessions_expires_at ON sessions(expires_at)"
    )
    connection.execute(
        "CREATE INDEX idx_invite_codes_expires_at ON invite_codes(expires_at)"
    )
    foreign_key_errors = connection.execute("PRAGMA foreign_key_check").fetchall()
    if foreign_key_errors:
        raise RuntimeError("Foreign key validation failed after multi-user migration.")
