import sqlite3
from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional, Sequence

from .versions import (
    v0001_initial,
    v0002_recovery_code,
    v0003_multi_user,
    v0004_auth_rate_limits,
    v0005_admin_audit_logs,
)


MigrationFunction = Callable[[sqlite3.Connection], None]


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    upgrade: MigrationFunction


@dataclass(frozen=True)
class MigrationStatus:
    version: int
    name: str
    applied: bool
    applied_at: Optional[datetime]


class MigrationError(RuntimeError):
    pass


MIGRATIONS: tuple[Migration, ...] = (
    Migration(v0001_initial.VERSION, v0001_initial.NAME, v0001_initial.upgrade),
    Migration(
        v0002_recovery_code.VERSION,
        v0002_recovery_code.NAME,
        v0002_recovery_code.upgrade,
    ),
    Migration(v0003_multi_user.VERSION, v0003_multi_user.NAME, v0003_multi_user.upgrade),
    Migration(
        v0004_auth_rate_limits.VERSION,
        v0004_auth_rate_limits.NAME,
        v0004_auth_rate_limits.upgrade,
    ),
    Migration(
        v0005_admin_audit_logs.VERSION,
        v0005_admin_audit_logs.NAME,
        v0005_admin_audit_logs.upgrade,
    ),
)


def _validate_registry(migrations: Sequence[Migration]) -> None:
    versions = [migration.version for migration in migrations]
    expected = list(range(1, len(migrations) + 1))
    if versions != expected:
        raise MigrationError(
            f"Migration versions must be consecutive and ordered: expected {expected}, got {versions}."
        )

    names = [migration.name for migration in migrations]
    if len(names) != len(set(names)):
        raise MigrationError("Migration names must be unique.")


def _ensure_migration_table(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL UNIQUE,
            applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
        """
    )
    connection.commit()


def _validate_applied_migrations(
    connection: sqlite3.Connection,
    migrations: Sequence[Migration],
) -> None:
    known = {migration.version: migration for migration in migrations}
    rows = connection.execute(
        "SELECT version, name FROM schema_migrations ORDER BY version"
    ).fetchall()

    for row in rows:
        migration = known.get(row["version"])
        if migration is None:
            raise MigrationError(
                f"Database has unknown migration version {row['version']}."
            )
        if migration.name != row["name"]:
            raise MigrationError(
                f"Migration {row['version']} name mismatch: "
                f"database={row['name']!r}, code={migration.name!r}."
            )


def apply_migrations(
    connection: sqlite3.Connection,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> list[Migration]:
    _validate_registry(migrations)
    _ensure_migration_table(connection)
    _validate_applied_migrations(connection, migrations)
    applied_now: list[Migration] = []

    for migration in migrations:
        try:
            connection.execute("BEGIN IMMEDIATE")
            existing = connection.execute(
                "SELECT name FROM schema_migrations WHERE version = ?",
                (migration.version,),
            ).fetchone()
            if existing is not None:
                if existing["name"] != migration.name:
                    raise MigrationError(
                        f"Migration {migration.version} changed after it was applied."
                    )
                connection.commit()
                continue

            migration.upgrade(connection)
            connection.execute(
                "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
                (migration.version, migration.name),
            )
            connection.execute(f"PRAGMA user_version = {migration.version}")
            connection.commit()
            applied_now.append(migration)
        except Exception:
            connection.rollback()
            raise

    return applied_now


def get_migration_status(
    connection: sqlite3.Connection,
    migrations: Sequence[Migration] = MIGRATIONS,
) -> list[MigrationStatus]:
    _validate_registry(migrations)
    migration_table_exists = connection.execute(
        """
        SELECT 1 FROM sqlite_master
        WHERE type = 'table' AND name = 'schema_migrations'
        """
    ).fetchone()
    if migration_table_exists:
        _validate_applied_migrations(connection, migrations)
        rows = {
            row["version"]: row
            for row in connection.execute(
                "SELECT version, name, applied_at FROM schema_migrations"
            ).fetchall()
        }
    else:
        rows = {}
    return [
        MigrationStatus(
            version=migration.version,
            name=migration.name,
            applied=migration.version in rows,
            applied_at=(
                datetime.fromisoformat(rows[migration.version]["applied_at"])
                if migration.version in rows
                else None
            ),
        )
        for migration in migrations
    ]


def latest_version() -> int:
    return MIGRATIONS[-1].version if MIGRATIONS else 0
