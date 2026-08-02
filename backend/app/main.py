import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date, timedelta
from typing import List, Optional

from fastapi import Cookie, Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection, init_database
from .auth import (
    SESSION_COOKIE,
    SESSION_DAYS,
    create_session,
    get_optional_account,
    hash_password,
    hash_session_token,
    normalize_email,
    require_account,
    verify_password,
)
from .schemas import (
    AccountLogin,
    AccountRegister,
    AuthSession,
    ExportData,
    Insights,
    Period,
    PeriodCreate,
    PeriodUpdate,
    Profile,
    ProfileSetup,
)
from .services import calculate_insights, row_to_period, row_to_profile, utc_now


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_database()
    yield


app = FastAPI(
    title="Luna API",
    description="Kişisel döngü takip uygulaması API'si",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
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
        secure=False,
        path="/",
    )


@app.post("/api/auth/register", response_model=AuthSession)
def register(
    payload: AccountRegister,
    response: Response,
    connection: sqlite3.Connection = Depends(get_connection),
) -> AuthSession:
    existing_account = connection.execute(
        "SELECT id FROM accounts LIMIT 1"
    ).fetchone()
    if existing_account:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Bu uygulamada zaten bir hesap var. Giris yapabilirsin.",
        )

    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="Isim bos birakilamaz.")
    email = normalize_email(payload.email)
    salt, password_digest = hash_password(payload.password)
    period_end = payload.last_period_start + timedelta(
        days=payload.average_period_length - 1
    )

    connection.execute(
        """
        INSERT INTO accounts (id, email, password_hash, password_salt)
        VALUES (1, ?, ?, ?)
        """,
        (email, password_digest, salt),
    )
    connection.execute(
        """
        INSERT INTO profile (
            id, name, average_cycle_length, average_period_length
        ) VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            average_cycle_length = excluded.average_cycle_length,
            average_period_length = excluded.average_period_length,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            clean_name,
            payload.average_cycle_length,
            payload.average_period_length,
        ),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO periods (start_date, end_date, flow, symptoms, notes)
        VALUES (?, ?, 'medium', '[]', 'Onboarding setup')
        """,
        (payload.last_period_start.isoformat(), period_end.isoformat()),
    )
    connection.commit()

    token = create_session(connection, 1)
    set_session_cookie(response, token)
    return AuthSession(email=email)


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
    if account is None or not verify_password(
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
    return AuthSession(email=account["email"])


@app.get("/api/auth/session", response_model=Optional[AuthSession])
def auth_session(
    account: Optional[sqlite3.Row] = Depends(get_optional_account),
) -> Optional[AuthSession]:
    return AuthSession(email=account["email"]) if account else None


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


@app.get(
    "/api/profile",
    response_model=Optional[Profile],
    dependencies=[Depends(require_account)],
)
def get_profile(
    connection: sqlite3.Connection = Depends(get_connection),
) -> Optional[Profile]:
    row = connection.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return row_to_profile(row)


@app.put(
    "/api/profile",
    response_model=Profile,
    dependencies=[Depends(require_account)],
)
def setup_profile(
    payload: ProfileSetup,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Profile:
    clean_name = payload.name.strip()
    if not clean_name:
        raise HTTPException(status_code=422, detail="Name cannot be empty.")

    period_end = payload.last_period_start + timedelta(
        days=payload.average_period_length - 1
    )
    connection.execute(
        """
        INSERT INTO profile (
            id, name, average_cycle_length, average_period_length
        ) VALUES (1, ?, ?, ?)
        ON CONFLICT(id) DO UPDATE SET
            name = excluded.name,
            average_cycle_length = excluded.average_cycle_length,
            average_period_length = excluded.average_period_length,
            updated_at = CURRENT_TIMESTAMP
        """,
        (
            clean_name,
            payload.average_cycle_length,
            payload.average_period_length,
        ),
    )
    connection.execute(
        """
        INSERT OR IGNORE INTO periods (start_date, end_date, flow, symptoms, notes)
        VALUES (?, ?, 'medium', '[]', 'Onboarding setup')
        """,
        (payload.last_period_start.isoformat(), period_end.isoformat()),
    )
    connection.commit()
    row = connection.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return row_to_profile(row)


@app.get(
    "/api/periods",
    response_model=List[Period],
    dependencies=[Depends(require_account)],
)
def list_periods(connection: sqlite3.Connection = Depends(get_connection)) -> List[Period]:
    rows = connection.execute(
        "SELECT * FROM periods ORDER BY start_date DESC"
    ).fetchall()
    return [row_to_period(row) for row in rows]


@app.post(
    "/api/periods",
    response_model=Period,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_account)],
)
def create_period(
    payload: PeriodCreate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Period:
    try:
        cursor = connection.execute(
            """
            INSERT INTO periods (start_date, end_date, flow, symptoms, notes)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
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
        "SELECT * FROM periods WHERE id = ?", (cursor.lastrowid,)
    ).fetchone()
    return row_to_period(row)


@app.put(
    "/api/periods/{period_id}",
    response_model=Period,
    dependencies=[Depends(require_account)],
)
def update_period(
    period_id: int,
    payload: PeriodUpdate,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Period:
    existing = connection.execute(
        "SELECT id FROM periods WHERE id = ?", (period_id,)
    ).fetchone()
    if existing is None:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")

    try:
        connection.execute(
            """
            UPDATE periods
            SET start_date = ?, end_date = ?, flow = ?, symptoms = ?, notes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                payload.start_date.isoformat(),
                payload.end_date.isoformat() if payload.end_date else None,
                payload.flow,
                json.dumps(payload.symptoms, ensure_ascii=False),
                payload.notes.strip(),
                period_id,
            ),
        )
        connection.commit()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(
            status_code=409,
            detail="Bu başlangıç tarihi için zaten bir kayıt var.",
        ) from exc

    row = connection.execute(
        "SELECT * FROM periods WHERE id = ?", (period_id,)
    ).fetchone()
    return row_to_period(row)


@app.delete(
    "/api/periods/{period_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_account)],
)
def delete_period(
    period_id: int,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    cursor = connection.execute("DELETE FROM periods WHERE id = ?", (period_id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get(
    "/api/insights",
    response_model=Insights,
    dependencies=[Depends(require_account)],
)
def insights(
    today: date = None,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Insights:
    rows = connection.execute("SELECT * FROM periods ORDER BY start_date").fetchall()
    periods = [row_to_period(row) for row in rows]
    profile_row = connection.execute("SELECT * FROM profile WHERE id = 1").fetchone()
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
    dependencies=[Depends(require_account)],
)
def export_data(
    connection: sqlite3.Connection = Depends(get_connection),
) -> ExportData:
    rows = connection.execute(
        "SELECT * FROM periods ORDER BY start_date"
    ).fetchall()
    profile_row = connection.execute("SELECT * FROM profile WHERE id = 1").fetchone()
    return ExportData(
        exported_at=utc_now(),
        profile=row_to_profile(profile_row),
        periods=[row_to_period(row) for row in rows],
    )
