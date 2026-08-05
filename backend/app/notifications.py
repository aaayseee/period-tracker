import json
import os
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
from typing import Callable, Optional
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from .services import calculate_insights, row_to_period, row_to_profile


DEFAULT_TIMEZONE = "Europe/Istanbul"
DEFAULT_REMINDER_TIME = "10:00"


class NotificationConfigurationError(RuntimeError):
    pass


class ExpiredPushSubscription(RuntimeError):
    pass


@dataclass(frozen=True)
class DispatchSummary:
    due_notifications: int = 0
    sent_messages: int = 0
    failed_messages: int = 0
    expired_subscriptions: int = 0


def get_vapid_public_key() -> str:
    return os.getenv("PERIOD_TRACKER_VAPID_PUBLIC_KEY", "").strip()


def _vapid_private_key() -> str:
    return os.getenv("PERIOD_TRACKER_VAPID_PRIVATE_KEY", "").strip()


def _vapid_subject() -> str:
    return os.getenv("PERIOD_TRACKER_VAPID_SUBJECT", "").strip()


def notifications_configured() -> bool:
    return bool(get_vapid_public_key() and _vapid_private_key() and _vapid_subject())


def validate_notification_configuration() -> None:
    if not notifications_configured():
        raise NotificationConfigurationError(
            "VAPID public/private key and subject must be configured."
        )


def send_web_push(subscription: dict, payload: dict) -> None:
    validate_notification_configuration()
    from pywebpush import WebPushException, webpush

    try:
        webpush(
            subscription_info={
                "endpoint": subscription["endpoint"],
                "keys": {
                    "p256dh": subscription["p256dh"],
                    "auth": subscription["auth"],
                },
            },
            data=json.dumps(payload, ensure_ascii=False),
            vapid_private_key=_vapid_private_key(),
            vapid_claims={"sub": _vapid_subject()},
            ttl=24 * 60 * 60,
            timeout=15,
        )
    except WebPushException as exc:
        status_code = getattr(exc.response, "status_code", None)
        if status_code in {404, 410}:
            raise ExpiredPushSubscription from exc
        raise


def test_notification_payload() -> dict:
    return {
        "title": "Luna",
        "body": "Bildirimlerin hazır. Hatırlatmalar yalnız seçtiğin zamanda gelecek.",
        "tag": "luna-notification-test",
        "url": "/",
    }


def _scheduled_payload(notification_type: str, target_date: date) -> dict:
    if notification_type == "pms_start":
        body = "Takviminde yeni bir dönem başladı. Kendine nazik davranmayı unutma."
    else:
        body = "Yaklaşan döngün için takvimini kontrol etmek isteyebilirsin."
    return {
        "title": "Luna",
        "body": body,
        "tag": f"luna-{notification_type}-{target_date.isoformat()}",
        "url": "/",
    }


def send_test_notification(
    connection: sqlite3.Connection,
    account_id: int,
    sender: Callable[[dict, dict], None] = send_web_push,
) -> DispatchSummary:
    subscriptions = connection.execute(
        "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE account_id = ?",
        (account_id,),
    ).fetchall()
    sent = failed = expired = 0
    for subscription in subscriptions:
        try:
            sender(dict(subscription), test_notification_payload())
            sent += 1
        except ExpiredPushSubscription:
            connection.execute(
                "DELETE FROM push_subscriptions WHERE id = ?", (subscription["id"],)
            )
            expired += 1
        except Exception:
            failed += 1
    connection.commit()
    return DispatchSummary(
        due_notifications=1 if subscriptions else 0,
        sent_messages=sent,
        failed_messages=failed,
        expired_subscriptions=expired,
    )


def dispatch_due_notifications(
    connection: sqlite3.Connection,
    now_utc: Optional[datetime] = None,
    sender: Callable[[dict, dict], None] = send_web_push,
) -> DispatchSummary:
    current_utc = now_utc or datetime.now(timezone.utc)
    if current_utc.tzinfo is None:
        current_utc = current_utc.replace(tzinfo=timezone.utc)

    preference_rows = connection.execute(
        """
        SELECT np.account_id, np.period_reminder_days, np.pms_reminder_enabled,
               np.reminder_time, np.timezone
        FROM notification_preferences np
        JOIN accounts a ON a.id = np.account_id
        WHERE np.enabled = 1 AND a.is_active = 1 AND a.role = 'user'
        """
    ).fetchall()

    due = sent = failed = expired = 0
    for preference in preference_rows:
        try:
            local_now = current_utc.astimezone(ZoneInfo(preference["timezone"]))
        except ZoneInfoNotFoundError:
            local_now = current_utc.astimezone(ZoneInfo(DEFAULT_TIMEZONE))
        if local_now.strftime("%H:%M") < preference["reminder_time"]:
            continue

        account_id = preference["account_id"]
        period_rows = connection.execute(
            "SELECT * FROM periods WHERE account_id = ? ORDER BY start_date",
            (account_id,),
        ).fetchall()
        profile_row = connection.execute(
            "SELECT * FROM profile WHERE account_id = ?", (account_id,)
        ).fetchone()
        profile = row_to_profile(profile_row)
        insights = calculate_insights(
            [row_to_period(row) for row in period_rows],
            local_now.date(),
            profile.average_cycle_length if profile else 28,
            profile.average_period_length if profile else 5,
        )
        candidates = [
            (
                "period_reminder",
                insights.next_period_start
                - timedelta(days=preference["period_reminder_days"]),
            )
        ]
        if preference["pms_reminder_enabled"]:
            candidates.append(("pms_start", insights.pms_window_start))

        subscriptions = connection.execute(
            "SELECT id, endpoint, p256dh, auth FROM push_subscriptions WHERE account_id = ?",
            (account_id,),
        ).fetchall()
        for notification_type, target_date in candidates:
            if target_date != local_now.date() or not subscriptions:
                continue
            already_sent = connection.execute(
                """
                SELECT 1 FROM notification_deliveries
                WHERE account_id = ? AND notification_type = ? AND target_date = ?
                """,
                (account_id, notification_type, target_date.isoformat()),
            ).fetchone()
            if already_sent:
                continue

            due += 1
            delivered = 0
            for subscription in subscriptions:
                try:
                    sender(
                        dict(subscription),
                        _scheduled_payload(notification_type, target_date),
                    )
                    delivered += 1
                    sent += 1
                except ExpiredPushSubscription:
                    connection.execute(
                        "DELETE FROM push_subscriptions WHERE id = ?",
                        (subscription["id"],),
                    )
                    expired += 1
                except Exception:
                    failed += 1
            if delivered:
                connection.execute(
                    """
                    INSERT OR IGNORE INTO notification_deliveries (
                        account_id, notification_type, target_date
                    ) VALUES (?, ?, ?)
                    """,
                    (account_id, notification_type, target_date.isoformat()),
                )
    connection.commit()
    return DispatchSummary(due, sent, failed, expired)
