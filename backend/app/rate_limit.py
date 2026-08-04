import hashlib
import ipaddress
import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta

from fastapi import HTTPException, Request, status


@dataclass(frozen=True)
class RateLimitPolicy:
    attempts: int
    window_seconds: int


def _positive_int(name: str, default: int, maximum: int) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError:
        return default
    return max(1, min(maximum, value))


POLICIES = {
    "login": RateLimitPolicy(
        _positive_int("PERIOD_TRACKER_LOGIN_ATTEMPTS", 5, 100),
        _positive_int("PERIOD_TRACKER_LOGIN_WINDOW_SECONDS", 900, 86400),
    ),
    "recover": RateLimitPolicy(
        _positive_int("PERIOD_TRACKER_RECOVERY_ATTEMPTS", 5, 100),
        _positive_int("PERIOD_TRACKER_RECOVERY_WINDOW_SECONDS", 1800, 86400),
    ),
    "register": RateLimitPolicy(
        _positive_int("PERIOD_TRACKER_REGISTER_ATTEMPTS", 10, 100),
        _positive_int("PERIOD_TRACKER_REGISTER_WINDOW_SECONDS", 3600, 86400),
    ),
    "change_password": RateLimitPolicy(5, 900),
}


def _trust_proxy_headers() -> bool:
    return os.getenv("PERIOD_TRACKER_TRUST_PROXY", "false").lower() in {
        "1",
        "true",
        "yes",
    }


def _client_ip(request: Request) -> str:
    candidate = request.client.host if request.client else "unknown"
    if _trust_proxy_headers():
        forwarded = request.headers.get("x-forwarded-for", "").split(",", 1)[0].strip()
        if forwarded:
            candidate = forwarded
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return candidate[:64]


def _bucket_hash(action: str, request: Request, subject: str) -> str:
    normalized_subject = subject.strip().lower()[:254]
    raw = f"{action}|{_client_ip(request)}|{normalized_subject}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def enforce_rate_limit(
    connection: sqlite3.Connection,
    action: str,
    request: Request,
    subject: str,
) -> str:
    policy = POLICIES[action]
    bucket_hash = _bucket_hash(action, request, subject)
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=policy.window_seconds)
    row = connection.execute(
        """
        SELECT COUNT(id) AS attempts, MIN(occurred_at) AS first_attempt
        FROM auth_rate_limit_events
        WHERE bucket_hash = ? AND occurred_at > ?
        """,
        (bucket_hash, cutoff.strftime("%Y-%m-%d %H:%M:%S")),
    ).fetchone()
    if row["attempts"] >= policy.attempts:
        first_attempt = datetime.fromisoformat(row["first_attempt"])
        retry_at = first_attempt + timedelta(seconds=policy.window_seconds)
        retry_after = max(1, int((retry_at - now).total_seconds()) + 1)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Çok fazla başarısız deneme yapıldı. Lütfen bir süre sonra tekrar dene.",
            headers={"Retry-After": str(retry_after)},
        )
    return bucket_hash


def record_failed_attempt(
    connection: sqlite3.Connection,
    action: str,
    bucket_hash: str,
) -> None:
    cleanup_before = datetime.utcnow() - timedelta(days=2)
    connection.execute(
        "DELETE FROM auth_rate_limit_events WHERE occurred_at <= ?",
        (cleanup_before.strftime("%Y-%m-%d %H:%M:%S"),),
    )
    connection.execute(
        """
        INSERT INTO auth_rate_limit_events (bucket_hash, action)
        VALUES (?, ?)
        """,
        (bucket_hash, action),
    )
    connection.commit()


def clear_rate_limit(connection: sqlite3.Connection, bucket_hash: str) -> None:
    connection.execute(
        "DELETE FROM auth_rate_limit_events WHERE bucket_hash = ?",
        (bucket_hash,),
    )
