import sqlite3


VERSION = 6
NAME = "web_push_notifications"


def upgrade(connection: sqlite3.Connection) -> None:
    connection.execute(
        """
        CREATE TABLE notification_preferences (
            account_id INTEGER PRIMARY KEY,
            enabled INTEGER NOT NULL DEFAULT 0 CHECK (enabled IN (0, 1)),
            period_reminder_days INTEGER NOT NULL DEFAULT 2
                CHECK (period_reminder_days BETWEEN 0 AND 7),
            pms_reminder_enabled INTEGER NOT NULL DEFAULT 1
                CHECK (pms_reminder_enabled IN (0, 1)),
            reminder_time TEXT NOT NULL DEFAULT '10:00'
                CHECK (reminder_time GLOB '[0-2][0-9]:[0-5][0-9]'),
            timezone TEXT NOT NULL DEFAULT 'Europe/Istanbul',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE TABLE push_subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_id INTEGER NOT NULL,
            endpoint TEXT NOT NULL UNIQUE,
            p256dh TEXT NOT NULL,
            auth TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )
    connection.execute(
        """
        CREATE INDEX idx_push_subscriptions_account
        ON push_subscriptions(account_id)
        """
    )
    connection.execute(
        """
        CREATE TABLE notification_deliveries (
            account_id INTEGER NOT NULL,
            notification_type TEXT NOT NULL
                CHECK (notification_type IN ('period_reminder', 'pms_start')),
            target_date TEXT NOT NULL,
            sent_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (account_id, notification_type, target_date),
            FOREIGN KEY (account_id) REFERENCES accounts(id) ON DELETE CASCADE
        )
        """
    )

