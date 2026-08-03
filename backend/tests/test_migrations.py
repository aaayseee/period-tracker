import sqlite3

import pytest

from app.database import connect, init_database
from app.migrations import MIGRATIONS, Migration, apply_migrations, get_migration_status


def table_names(connection: sqlite3.Connection) -> set[str]:
    return {
        row["name"]
        for row in connection.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()
    }


def test_fresh_database_applies_all_migrations_idempotently(tmp_path):
    database_path = tmp_path / "fresh.db"

    with connect(database_path) as connection:
        assert not any(status.applied for status in get_migration_status(connection))
        assert "schema_migrations" not in table_names(connection)

    init_database(database_path)
    init_database(database_path)

    with connect(database_path) as connection:
        assert {
            "accounts",
            "periods",
            "profile",
            "schema_migrations",
            "sessions",
        }.issubset(table_names(connection))
        assert [
            row["version"]
            for row in connection.execute(
                "SELECT version FROM schema_migrations ORDER BY version"
            ).fetchall()
        ] == [1, 2]
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2
        assert "recovery_code_hash" in {
            row["name"]
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        assert all(status.applied for status in get_migration_status(connection))


def test_existing_database_is_baselined_and_preserves_data(tmp_path):
    database_path = tmp_path / "legacy.db"
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE accounts (
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
            INSERT INTO accounts (id, email, password_hash, password_salt)
            VALUES (1, 'legacy@example.com', 'hash', 'salt')
            """
        )
        connection.commit()

    init_database(database_path)

    with connect(database_path) as connection:
        account = connection.execute(
            "SELECT email, password_hash, password_salt FROM accounts WHERE id = 1"
        ).fetchone()
        assert dict(account) == {
            "email": "legacy@example.com",
            "password_hash": "hash",
            "password_salt": "salt",
        }
        assert "recovery_code_hash" in {
            row["name"]
            for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
        }
        assert connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0] == 2


def test_failed_migration_rolls_back_schema_and_version(tmp_path):
    database_path = tmp_path / "rollback.db"
    init_database(database_path)

    def failing_upgrade(connection: sqlite3.Connection) -> None:
        connection.execute("CREATE TABLE should_be_rolled_back (id INTEGER PRIMARY KEY)")
        raise RuntimeError("planned migration failure")

    migrations = (
        *MIGRATIONS,
        Migration(version=3, name="failing_test_migration", upgrade=failing_upgrade),
    )

    with connect(database_path) as connection:
        with pytest.raises(RuntimeError, match="planned migration failure"):
            apply_migrations(connection, migrations)

    with connect(database_path) as connection:
        assert "should_be_rolled_back" not in table_names(connection)
        assert connection.execute(
            "SELECT COUNT(*) FROM schema_migrations WHERE version = 3"
        ).fetchone()[0] == 0
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 2


def test_incompatible_legacy_schema_is_not_baselined(tmp_path):
    database_path = tmp_path / "incompatible.db"
    with connect(database_path) as connection:
        connection.execute(
            """
            CREATE TABLE accounts (
                id INTEGER PRIMARY KEY,
                email TEXT NOT NULL,
                password_hash TEXT NOT NULL
            )
            """
        )
        connection.commit()

    with pytest.raises(RuntimeError, match="missing columns"):
        init_database(database_path)

    with connect(database_path) as connection:
        assert connection.execute(
            "SELECT COUNT(*) FROM schema_migrations"
        ).fetchone()[0] == 0
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 0
