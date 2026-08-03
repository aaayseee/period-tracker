import argparse

from ..database import connect, get_database_path
from . import apply_migrations, get_migration_status, latest_version


def main() -> None:
    parser = argparse.ArgumentParser(description="Luna SQLite migration manager")
    parser.add_argument(
        "command",
        choices=("status", "upgrade"),
        help="Show migration status or apply all pending migrations.",
    )
    args = parser.parse_args()
    database_path = get_database_path()

    with connect(database_path) as connection:
        if args.command == "upgrade":
            applied = apply_migrations(connection)
            if applied:
                for migration in applied:
                    print(f"Applied {migration.version:04d} {migration.name}")
            else:
                print("Database is already up to date.")

        statuses = get_migration_status(connection)

    print(f"Database: {database_path.resolve()}")
    for status in statuses:
        marker = "x" if status.applied else " "
        applied_at = (
            f" ({status.applied_at.isoformat(sep=' ')})"
            if status.applied_at
            else ""
        )
        print(f"[{marker}] {status.version:04d} {status.name}{applied_at}")
    print(f"Latest version: {latest_version():04d}")


if __name__ == "__main__":
    main()
