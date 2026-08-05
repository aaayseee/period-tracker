import argparse
import base64
import os
import time
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from .database import connect, init_database
from .notifications import (
    dispatch_due_notifications,
    validate_notification_configuration,
)


def _base64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def init_env(output: Path, subject: str) -> None:
    if output.exists():
        raise SystemExit(f"Refusing to overwrite existing file: {output}")
    if not (subject.startswith("mailto:") or subject.startswith("https://")):
        raise SystemExit("VAPID subject must start with mailto: or https://")

    private_key = ec.generate_private_key(ec.SECP256R1())
    private_der = private_key.private_bytes(
        serialization.Encoding.DER,
        serialization.PrivateFormat.PKCS8,
        serialization.NoEncryption(),
    )
    public_numbers = private_key.public_key().public_numbers()
    public_bytes = (
        b"\x04"
        + public_numbers.x.to_bytes(32, "big")
        + public_numbers.y.to_bytes(32, "big")
    )
    output.write_text(
        "\n".join(
            [
                f"PERIOD_TRACKER_VAPID_PRIVATE_KEY={_base64url(private_der)}",
                f"PERIOD_TRACKER_VAPID_PUBLIC_KEY={_base64url(public_bytes)}",
                f"PERIOD_TRACKER_VAPID_SUBJECT={subject}",
                "PERIOD_TRACKER_NOTIFICATION_INTERVAL_SECONDS=300",
                "",
            ]
        ),
        encoding="utf-8",
    )


def send_once() -> None:
    validate_notification_configuration()
    init_database()
    with connect() as connection:
        summary = dispatch_due_notifications(connection)
    print(
        f"due={summary.due_notifications} sent={summary.sent_messages} "
        f"failed={summary.failed_messages} expired={summary.expired_subscriptions}"
    )


def schedule() -> None:
    validate_notification_configuration()
    init_database()
    interval = int(os.getenv("PERIOD_TRACKER_NOTIFICATION_INTERVAL_SECONDS", "300"))
    interval = max(60, min(interval, 3600))
    while True:
        try:
            send_once()
        except Exception as exc:
            print(f"notification dispatch failed: {exc}", flush=True)
        time.sleep(interval)


def status() -> None:
    validate_notification_configuration()
    init_database()
    with connect() as connection:
        connection.execute("SELECT 1 FROM push_subscriptions LIMIT 1").fetchone()
    print("ok")


def main() -> None:
    parser = argparse.ArgumentParser(description="Luna Web Push utilities")
    subparsers = parser.add_subparsers(dest="command", required=True)
    init_parser = subparsers.add_parser("init-env")
    init_parser.add_argument("--output", type=Path, required=True)
    init_parser.add_argument("--subject", required=True)
    subparsers.add_parser("send-once")
    subparsers.add_parser("schedule")
    subparsers.add_parser("status")
    args = parser.parse_args()

    if args.command == "init-env":
        init_env(args.output, args.subject)
    elif args.command == "send-once":
        send_once()
    elif args.command == "schedule":
        schedule()
    else:
        status()


if __name__ == "__main__":
    main()
