from datetime import datetime, timezone

from app.database import connect, init_database
from app.notifications import dispatch_due_notifications


def seed_notification_account(connection):
    account_id = connection.execute(
        """
        INSERT INTO accounts (
            email, password_hash, password_salt, recovery_code_hash, role
        ) VALUES ('notify@example.com', 'hash', 'salt', 'recovery', 'user')
        """
    ).lastrowid
    connection.execute(
        """
        INSERT INTO profile (
            account_id, name, average_cycle_length, average_period_length
        ) VALUES (?, 'Notify', 28, 5)
        """,
        (account_id,),
    )
    connection.execute(
        """
        INSERT INTO periods (
            account_id, start_date, end_date, flow, symptoms, notes
        ) VALUES (?, '2026-07-10', '2026-07-14', 'medium', '[]', '')
        """,
        (account_id,),
    )
    connection.execute(
        """
        INSERT INTO notification_preferences (
            account_id, enabled, period_reminder_days, pms_reminder_enabled,
            reminder_time, timezone
        ) VALUES (?, 1, 2, 0, '10:00', 'Europe/Istanbul')
        """,
        (account_id,),
    )
    connection.execute(
        """
        INSERT INTO push_subscriptions (account_id, endpoint, p256dh, auth)
        VALUES (?, 'https://push.example/subscription', 'p256dh-value', 'auth-value')
        """,
        (account_id,),
    )
    connection.commit()
    return account_id


def test_due_period_notification_is_sent_once(tmp_path):
    database_path = tmp_path / "notifications.db"
    init_database(database_path)
    sent_payloads = []

    with connect(database_path) as connection:
        account_id = seed_notification_account(connection)
        now = datetime(2026, 8, 5, 7, 5, tzinfo=timezone.utc)
        first = dispatch_due_notifications(
            connection,
            now_utc=now,
            sender=lambda subscription, payload: sent_payloads.append(
                (subscription, payload)
            ),
        )
        second = dispatch_due_notifications(
            connection,
            now_utc=now,
            sender=lambda subscription, payload: sent_payloads.append(
                (subscription, payload)
            ),
        )

        assert first.due_notifications == 1
        assert first.sent_messages == 1
        assert second.due_notifications == 0
        assert len(sent_payloads) == 1
        assert sent_payloads[0][1]["title"] == "Luna"
        assert "2026-08-05" in sent_payloads[0][1]["tag"]
        delivery = connection.execute(
            """
            SELECT notification_type, target_date
            FROM notification_deliveries WHERE account_id = ?
            """,
            (account_id,),
        ).fetchone()
        assert dict(delivery) == {
            "notification_type": "period_reminder",
            "target_date": "2026-08-05",
        }


def test_notification_waits_until_selected_local_time(tmp_path):
    database_path = tmp_path / "notifications-time.db"
    init_database(database_path)

    with connect(database_path) as connection:
        seed_notification_account(connection)
        summary = dispatch_due_notifications(
            connection,
            now_utc=datetime(2026, 8, 5, 6, 59, tzinfo=timezone.utc),
            sender=lambda subscription, payload: None,
        )
        assert summary.due_notifications == 0
        assert connection.execute(
            "SELECT COUNT(*) FROM notification_deliveries"
        ).fetchone()[0] == 0

