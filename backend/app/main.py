import json
import os
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, datetime, timedelta
from typing import List, Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection, init_database
from .auth import (
    SESSION_COOKIE,
    SESSION_DAYS,
    create_session,
    generate_invite_code,
    generate_recovery_code,
    get_optional_account,
    hash_invite_code,
    hash_password,
    hash_recovery_code,
    hash_session_token,
    normalize_email,
    require_account,
    require_admin_account,
    require_user_account,
    verify_password,
    verify_recovery_code,
)
from .schemas import (
    AccountLogin,
    AccountRegister,
    AdminInvite,
    AdminInviteCreate,
    AdminInviteCreated,
    AdminUser,
    AdminUserStatusUpdate,
    AuthSession,
    ExportData,
    Insights,
    Period,
    PeriodCreate,
    PeriodUpdate,
    PasswordChange,
    PasswordRecovery,
    PasswordRecoveryResult,
    Profile,
    ProfileUpdate,
    RecoveryCodeResult,
    RegistrationResult,
    RestoreRequest,
    RestoreResult,
)
from .services import calculate_insights, row_to_period, row_to_profile, utc_now


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Luna API",
    description="Kişisel döngü takip uygulaması API'si",
    version="0.2.0",
    lifespan=lifespan,
)

cors_origins = [
    origin.strip()
    for origin in os.getenv(
        "PERIOD_TRACKER_CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


def set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=SESSION_COOKIE,
        value=token,
        max_age=SESSION_DAYS * 24 * 60 * 60,
        httponly=True,
        samesite="strict",
        secure=os.getenv("PERIOD_TRACKER_SECURE_COOKIE", "false").lower()
        in {"1", "true", "yes"},
        path="/",
    )


@app.post("/api/auth/register", response_model=RegistrationResult)
def register(
    payload: AccountRegister,
    response: Response,
    connection: sqlite3.Connection = Depends(get_connection),
) -> RegistrationResult:
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="Isim bos birakilamaz.")
    email = normalize_email(payload.email)
    salt, password_digest = hash_password(payload.password)
    recovery_code = generate_recovery_code()
    period_end = payload.last_period_start + timedelta(
        days=payload.average_period_length - 1
    )

    try:
        connection.execute("BEGIN IMMEDIATE")
        if connection.execute(
            "SELECT 1 FROM accounts WHERE email = ? COLLATE NOCASE", (email,)
        ).fetchone():
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Bu e-posta adresi zaten kullanılıyor.",
            )
        invite = connection.execute(
            """
            SELECT * FROM invite_codes
            WHERE code_hash = ?
              AND revoked_at IS NULL
              AND expires_at > CURRENT_TIMESTAMP
              AND use_count < max_uses
            """,
            (hash_invite_code(payload.invite_code),),
        ).fetchone()
        if invite is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Davet kodu geçersiz, süresi dolmuş veya kullanım hakkı bitmiş.",
            )

        cursor = connection.execute(
            """
            INSERT INTO accounts (
                email, password_hash, password_salt, recovery_code_hash, role
            ) VALUES (?, ?, ?, ?, 'user')
            """,
            (email, password_digest, salt, hash_recovery_code(recovery_code)),
        )
        account_id = cursor.lastrowid
        connection.execute(
            """
            INSERT INTO profile (
                account_id, name, average_cycle_length, average_period_length
            ) VALUES (?, ?, ?, ?)
            """,
            (
                account_id,
                clean_name,
                payload.average_cycle_length,
                payload.average_period_length,
            ),
        )
        connection.execute(
            """
            INSERT INTO periods (
                account_id, start_date, end_date, flow, symptoms, notes
            ) VALUES (?, ?, ?, 'medium', '[]', 'Onboarding setup')
            """,
            (account_id, payload.last_period_start.isoformat(), period_end.isoformat()),
        )
        connection.execute(
            "UPDATE invite_codes SET use_count = use_count + 1 WHERE id = ?",
            (invite["id"],),
        )
        token = create_session(connection, account_id, commit=False)
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Hesap oluşturulamadı; e-posta adresini kontrol et.",
        ) from exc
    set_session_cookie(response, token)
    return RegistrationResult(email=email, role="user", recovery_code=recovery_code)


@app.post("/api/auth/login", response_model=AuthSession)
def login(
    payload: AccountLogin,
    response: Response,
    connection: sqlite3.Connection = Depends(get_connection),
) -> AuthSession:
    email = normalize_email(payload.email)
    account = connection.execute(
        "SELECT * FROM accounts WHERE email = ? COLLATE NOCASE", (email,)
    ).fetchone()
    if account is None or not account["is_active"] or not verify_password(
        payload.password,
        account["password_salt"],
        account["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya parola hatali.",
        )

    token = create_session(connection, account["id"])
    set_session_cookie(response, token)
    return AuthSession(email=account["email"], role=account["role"])


@app.get("/api/auth/session", response_model=Optional[AuthSession])
def auth_session(
    account: Optional[sqlite3.Row] = Depends(get_optional_account),
) -> Optional[AuthSession]:
    return AuthSession(email=account["email"], role=account["role"]) if account else None


@app.post(
    "/api/auth/change-password",
    response_model=AuthSession,
)
def change_password(
    payload: PasswordChange,
    response: Response,
    account: sqlite3.Row = Depends(require_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> AuthSession:
    if not verify_password(
        payload.current_password,
        account["password_salt"],
        account["password_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Mevcut parola hatali.",
        )
    if payload.current_password == payload.new_password:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Yeni parola mevcut paroladan farkli olmali.",
        )

    salt, password_digest = hash_password(payload.new_password)
    connection.execute(
        """
        UPDATE accounts
        SET password_hash = ?, password_salt = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (password_digest, salt, account["id"]),
    )
    connection.execute(
        "DELETE FROM sessions WHERE account_id = ?", (account["id"],)
    )
    connection.commit()
    token = create_session(connection, account["id"])
    set_session_cookie(response, token)
    return AuthSession(email=account["email"], role=account["role"])


@app.post(
    "/api/auth/recovery-code",
    response_model=RecoveryCodeResult,
)
def rotate_recovery_code(
    account: sqlite3.Row = Depends(require_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> RecoveryCodeResult:
    recovery_code = generate_recovery_code()
    connection.execute(
        """
        UPDATE accounts
        SET recovery_code_hash = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (hash_recovery_code(recovery_code), account["id"]),
    )
    connection.commit()
    return RecoveryCodeResult(recovery_code=recovery_code)


@app.post(
    "/api/auth/recover",
    response_model=PasswordRecoveryResult,
)
def recover_password(
    payload: PasswordRecovery,
    response: Response,
    connection: sqlite3.Connection = Depends(get_connection),
) -> PasswordRecoveryResult:
    email = normalize_email(payload.email)
    account = connection.execute(
        "SELECT * FROM accounts WHERE email = ? COLLATE NOCASE", (email,)
    ).fetchone()
    if account is None or not account["is_active"] or not verify_recovery_code(
        payload.recovery_code,
        account["recovery_code_hash"],
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="E-posta veya kurtarma kodu hatali.",
        )

    salt, password_digest = hash_password(payload.new_password)
    new_recovery_code = generate_recovery_code()
    connection.execute(
        """
        UPDATE accounts
        SET password_hash = ?, password_salt = ?, recovery_code_hash = ?,
            updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (
            password_digest,
            salt,
            hash_recovery_code(new_recovery_code),
            account["id"],
        ),
    )
    connection.execute(
        "DELETE FROM sessions WHERE account_id = ?", (account["id"],)
    )
    connection.commit()
    token = create_session(connection, account["id"])
    set_session_cookie(response, token)
    return PasswordRecoveryResult(
        email=account["email"],
        role=account["role"],
        recovery_code=new_recovery_code,
    )


@app.post("/api/auth/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    response: Response,
    luna_session: Optional[str] = Cookie(default=None),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    if luna_session:
        connection.execute(
            "DELETE FROM sessions WHERE token_hash = ?",
            (hash_session_token(luna_session),),
        )
        connection.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@app.get("/api/admin/users", response_model=List[AdminUser])
def admin_list_users(
    _: sqlite3.Row = Depends(require_admin_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> List[AdminUser]:
    rows = connection.execute(
        """
        SELECT id, email, role, is_active, created_at, updated_at
        FROM accounts
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    return [AdminUser(**dict(row)) for row in rows]


@app.patch("/api/admin/users/{account_id}", response_model=AdminUser)
def admin_update_user_status(
    account_id: int,
    payload: AdminUserStatusUpdate,
    _: sqlite3.Row = Depends(require_admin_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> AdminUser:
    target = connection.execute(
        "SELECT * FROM accounts WHERE id = ?", (account_id,)
    ).fetchone()
    if target is None or target["role"] != "user":
        raise HTTPException(status_code=404, detail="Kullanıcı bulunamadı.")

    connection.execute(
        """
        UPDATE accounts
        SET is_active = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
        """,
        (int(payload.is_active), account_id),
    )
    if not payload.is_active:
        connection.execute("DELETE FROM sessions WHERE account_id = ?", (account_id,))
    connection.commit()
    row = connection.execute(
        """
        SELECT id, email, role, is_active, created_at, updated_at
        FROM accounts WHERE id = ?
        """,
        (account_id,),
    ).fetchone()
    return AdminUser(**dict(row))


@app.post(
    "/api/admin/invites",
    response_model=AdminInviteCreated,
    status_code=status.HTTP_201_CREATED,
)
def admin_create_invite(
    payload: AdminInviteCreate,
    admin: sqlite3.Row = Depends(require_admin_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> AdminInviteCreated:
    invite_code = generate_invite_code()
    expires_at = datetime.utcnow() + timedelta(days=payload.expiry_days)
    cursor = connection.execute(
        """
        INSERT INTO invite_codes (
            code_hash, created_by, expires_at, max_uses
        ) VALUES (?, ?, ?, ?)
        """,
        (
            hash_invite_code(invite_code),
            admin["id"],
            expires_at.strftime("%Y-%m-%d %H:%M:%S"),
            payload.max_uses,
        ),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM invite_codes WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return AdminInviteCreated(invite_code=invite_code, **dict(row))


@app.get("/api/admin/invites", response_model=List[AdminInvite])
def admin_list_invites(
    _: sqlite3.Row = Depends(require_admin_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> List[AdminInvite]:
    rows = connection.execute(
        """
        SELECT id, expires_at, max_uses, use_count, revoked_at, created_at
        FROM invite_codes
        ORDER BY created_at DESC, id DESC
        """
    ).fetchall()
    return [AdminInvite(**dict(row)) for row in rows]


@app.post("/api/admin/invites/{invite_id}/revoke", response_model=AdminInvite)
def admin_revoke_invite(
    invite_id: int,
    _: sqlite3.Row = Depends(require_admin_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> AdminInvite:
    cursor = connection.execute(
        """
        UPDATE invite_codes
        SET revoked_at = COALESCE(revoked_at, CURRENT_TIMESTAMP)
        WHERE id = ?
        """,
        (invite_id,),
    )
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Davet bulunamadı.")
    connection.commit()
    row = connection.execute(
        """
        SELECT id, expires_at, max_uses, use_count, revoked_at, created_at
        FROM invite_codes WHERE id = ?
        """,
        (invite_id,),
    ).fetchone()
    return AdminInvite(**dict(row))


@app.get(
    "/api/profile",
    response_model=Optional[Profile],
    dependencies=[Depends(require_user_account)],
)
def get_profile(
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Optional[Profile]:
    row = connection.execute(
        "SELECT * FROM profile WHERE account_id = ?", (account["id"],)
    ).fetchone()
    return row_to_profile(row)


@app.put(
    "/api/profile",
    response_model=Profile,
    dependencies=[Depends(require_user_account)],
)
def update_profile(
    payload: ProfileUpdate,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Profile:
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")

    connection.execute(
        """
        INSERT INTO profile (
            account_id, name, average_cycle_length, average_period_length
        ) VALUES (?, ?, ?, ?)
        ON CONFLICT(account_id) DO UPDATE SET
            name = excluded.name,
            average_cycle_length = excluded.average_cycle_length,
            average_period_length = excluded.average_period_length,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            account["id"],
            clean_name,
            payload.average_cycle_length,
            payload.average_period_length,
        ),
    )
    connection.commit()
    row = connection.execute(
        "SELECT * FROM profile WHERE account_id = ?", (account["id"],)
    ).fetchone()
    return row_to_profile(row)


@app.get(
    "/api/periods",
    response_model=List[Period],
    dependencies=[Depends(require_user_account)],
)
def list_periods(
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> List[Period]:
    rows = connection.execute(
        "SELECT * FROM periods WHERE account_id = ? ORDER BY start_date DESC",
        (account["id"],),
    ).fetchall()
    return [row_to_period(row) for row in rows]


@app.post(
    "/api/periods",
    response_model=Period,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_user_account)],
)
def create_period(
    payload: PeriodCreate,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Period:
    try:
        cursor = connection.execute(
            """
            INSERT INTO periods (
                account_id, start_date, end_date, flow, symptoms, notes
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                account["id"],
                payload.start_date.isoformat(),
                payload.end_date.isoformat() if payload.end_date else None,
                payload.flow,
                json.dumps(payload.symptoms, ensure_ascii=False),
                payload.notes.strip(),
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu başlangıç tarihi için zaten bir kayıt var.",
        ) from exc

    row = connection.execute(
        "SELECT * FROM periods WHERE id = ? AND account_id = ?",
        (cursor.lastrowid, account["id"]),
    ).fetchone()
    return row_to_period(row)


@app.put(
    "/api/periods/{period_id}",
    response_model=Period,
    dependencies=[Depends(require_user_account)],
)
def update_period(
    period_id: int,
    payload: PeriodUpdate,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Period:
    existing = connection.execute(
        "SELECT id FROM periods WHERE id = ? AND account_id = ?",
        (period_id, account["id"]),
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")

    try:
        connection.execute(
            """
            UPDATE periods
            SET start_date = ?, end_date = ?, flow = ?, symptoms = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND account_id = ?
            """,
            (
                payload.start_date.isoformat(),
                payload.end_date.isoformat() if payload.end_date else None,
                payload.flow,
                json.dumps(payload.symptoms, ensure_ascii=False),
                payload.notes.strip(),
                period_id,
                account["id"],
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Bu başlangıç tarihi için zaten bir kayıt var.",
        ) from exc

    row = connection.execute(
        "SELECT * FROM periods WHERE id = ? AND account_id = ?",
        (period_id, account["id"]),
    ).fetchone()
    return row_to_period(row)


@app.delete(
    "/api/periods/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_user_account)],
)
def delete_period(
    period_id: int,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    cursor = connection.execute(
        "DELETE FROM periods WHERE id = ? AND account_id = ?",
        (period_id, account["id"]),
    )
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/api/insights",
    response_model=Insights,
    dependencies=[Depends(require_user_account)],
)
def insights(
    today: date = None,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> Insights:
    rows = connection.execute(
        "SELECT * FROM periods WHERE account_id = ? ORDER BY start_date",
        (account["id"],),
    ).fetchall()
    periods = [row_to_period(row) for row in rows]
    profile_row = connection.execute(
        "SELECT * FROM profile WHERE account_id = ?", (account["id"],)
    ).fetchone()
    profile = row_to_profile(profile_row)
    return calculate_insights(
        periods,
        today or date.today(),
        profile.average_cycle_length if profile else 28,
        profile.average_period_length if profile else 5,
    )


@app.get(
    "/api/export",
    response_model=ExportData,
    dependencies=[Depends(require_user_account)],
)
def export_data(
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> ExportData:
    rows = connection.execute(
        "SELECT * FROM periods WHERE account_id = ? ORDER BY start_date",
        (account["id"],),
    ).fetchall()
    profile_row = connection.execute(
        "SELECT * FROM profile WHERE account_id = ?", (account["id"],)
    ).fetchone()
    return ExportData(
        exported_at=utc_now(),
        profile=row_to_profile(profile_row),
        periods=[row_to_period(row) for row in rows],
    )


@app.post(
    "/api/restore",
    response_model=RestoreResult,
    dependencies=[Depends(require_user_account)],
)
def restore_data(
    payload: RestoreRequest,
    account: sqlite3.Row = Depends(require_user_account),
    connection: sqlite3.Connection = Depends(get_connection),
) -> RestoreResult:
    imported_periods = 0
    skipped_periods = 0
    profile_restored = False

    try:
        connection.execute("BEGIN IMMEDIATE")

        if payload.mode == "replace":
            profile = payload.backup.profile
            if profile is None:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail="Tam geri yükleme için yedekte profil bulunmalıdır.",
                )

            connection.execute(
                "DELETE FROM periods WHERE account_id = ?", (account["id"],)
            )
            connection.execute(
                """
                INSERT INTO profile (
                    account_id, name, average_cycle_length, average_period_length,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?)
                ON CONFLICT(account_id) DO UPDATE SET
                    name = excluded.name,
                    average_cycle_length = excluded.average_cycle_length,
                    average_period_length = excluded.average_period_length,
                    created_at = excluded.created_at,
                    updated_at = excluded.updated_at
                """,
                (
                    account["id"],
                    profile.name.strip(),
                    profile.average_cycle_length,
                    profile.average_period_length,
                    profile.created_at.isoformat(),
                    profile.updated_at.isoformat(),
                ),
            )
            profile_restored = True

        existing_dates = {
            row["start_date"]
            for row in connection.execute(
                "SELECT start_date FROM periods WHERE account_id = ?",
                (account["id"],),
            ).fetchall()
        }

        for period in payload.backup.periods:
            start_date = period.start_date.isoformat()
            if start_date in existing_dates:
                skipped_periods += 1
                continue

            connection.execute(
                """
                INSERT INTO periods (
                    account_id, start_date, end_date, flow, symptoms, notes,
                    created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    account["id"],
                    start_date,
                    period.end_date.isoformat() if period.end_date else None,
                    period.flow,
                    json.dumps(period.symptoms, ensure_ascii=False),
                    period.notes.strip(),
                    period.created_at.isoformat(),
                    period.updated_at.isoformat(),
                ),
            )
            existing_dates.add(start_date)
            imported_periods += 1

        total_periods = connection.execute(
            "SELECT COUNT(*) AS count FROM periods WHERE account_id = ?",
            (account["id"],),
        ).fetchone()["count"]
        connection.commit()
    except HTTPException:
        connection.rollback()
        raise
    except sqlite3.IntegrityError as exc:
        connection.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Yedek mevcut verilerle uyumlu olmadığı için geri yüklenemedi.",
        ) from exc
    except Exception:
        connection.rollback()
        raise

    return RestoreResult(
        mode=payload.mode,
        imported_periods=imported_periods,
        skipped_periods=skipped_periods,
        total_periods=total_periods,
        profile_restored=profile_restored,
    )
