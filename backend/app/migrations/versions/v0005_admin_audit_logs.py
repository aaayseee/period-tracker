import sqlite3


VERSION = 5
NAME = "admin_audit_logs"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE admin_audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            admin_account_id INTEGER NOT NULL,
            admin_email TEXT NOT NULL,
            action TEXT NOT NULL,
            target_type TEXT,
            target_id INTEGER,
            details TEXT NOT NULL DEFAULT '{}',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (admin_account_id) REFERENCES accounts(id) ON DELETE RESTRICT
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_admin_audit_logs_created_at
        ON admin_audit_logs(created_at DESC, id DESC)
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_admin_audit_logs_admin
        ON admin_audit_logs(admin_account_id, created_at DESC)
        """
    )
