import json
import sqlite3
from typing import Dict, Optional


ALLOWED_DETAILS = {
    "admin_login": set(),
    "admin_logout": set(),
    "admin_password_changed": set(),
    "admin_password_recovered": set(),
    "admin_recovery_code_rotated": set(),
    "invite_created": {"expires_at", "max_uses"},
    "invite_revoked": {"max_uses", "use_count"},
    "user_status_changed": {"is_active"},
}


def record_admin_audit(
    connection: sqlite3.Connection,
    admin: sqlite3.Row,
    action: str,
    *,
    target_type: Optional[str] = None,
    target_id: Optional[int] = None,
    details: Optional[Dict[str, object]] = None,
) -> None:
    if admin["role"] != "admin":
        raise ValueError("Audit actor must be an admin account.")
    if action not in ALLOWED_DETAILS:
        raise ValueError(f"Unsupported admin audit action: {action}")

    safe_details = details or {}
    unexpected_keys = set(safe_details) - ALLOWED_DETAILS[action]
    if unexpected_keys:
        raise ValueError("Audit details contain fields that are not allow-listed.")

    connection.execute(
        """
        INSERT INTO admin_audit_logs (
            admin_account_id, admin_email, action, target_type, target_id, details
        ) VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            admin["id"],
            admin["email"],
            action,
            target_type,
            target_id,
            json.dumps(safe_details, ensure_ascii=False, sort_keys=True),
        ),
    )
