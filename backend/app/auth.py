import hashlib
import hmac
import os
import secrets
import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Cookie, Depends, HTTPException, status

from .database import get_connection


SESSION_COOKIE = "luna_session"
SESSION_DAYS = max(1, min(365, int(os.getenv("PERIOD_TRACKER_SESSION_DAYS", "30"))))
PASSWORD_ITERATIONS = 310_000


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if (
        "@" not in normalized
        or normalized.startswith("@")
        or normalized.endswith("@")
        or "." not in normalized.split("@")[-1]
    ):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Gecerli bir e-posta adresi gir.",
        )
    return normalized


def hash_password(password: str, salt: Optional[bytes] = None) -> tuple:
    password_salt = salt or secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt,
        PASSWORD_ITERATIONS,
    )
    return password_salt.hex(), digest.hex()


def verify_password(password: str, salt_hex: str, expected_hash: str) -> bool:
    _, actual_hash = hash_password(password, bytes.fromhex(salt_hex))
    return hmac.compare_digest(actual_hash, expected_hash)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def create_session(connection: sqlite3.Connection, account_id: int) -> str:
    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(days=SESSION_DAYS)
    connection.execute(
        "DELETE FROM sessions WHERE expires_at <= CURRENT_TIMESTAMP"
    )
    connection.execute(
        """
        INSERT INTO sessions (token_hash, account_id, expires_at)
        VALUES (?, ?, ?)
        """,
        (
            hash_session_token(token),
            account_id,
            expires_at.strftime("%Y-%m-%d %H:%M:%S"),
        ),
    )
    connection.commit()
    return token


def get_optional_account(
    luna_session: Optional[str] = Cookie(default=None),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Optional[sqlite3.Row]:
    if not luna_session:
        return None
    return connection.execute(
        """
        SELECT accounts.*
        FROM sessions
        JOIN accounts ON accounts.id = sessions.account_id
        WHERE sessions.token_hash = ? AND sessions.expires_at > CURRENT_TIMESTAMP
        """,
        (hash_session_token(luna_session),),
    ).fetchone()


def require_account(
    account: Optional[sqlite3.Row] = Depends(get_optional_account),
) -> sqlite3.Row:
    if account is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bu islem icin giris yapmalisin.",
        )
    return account
