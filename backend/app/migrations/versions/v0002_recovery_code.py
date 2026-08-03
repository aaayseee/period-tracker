import sqlite3


VERSION = 2
NAME = "add_recovery_code_hash"


def upgrade(connection: sqlite3.Connection) -> None:
    account_columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(accounts)").fetchall()
    }
    if "recovery_code_hash" not in account_columns:
        connection.execute(
            "ALTER TABLE accounts ADD COLUMN recovery_code_hash TEXT"
        )
