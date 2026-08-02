import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import date
from typing import List

from fastapi import Depends, FastAPI, HTTPException, Response, status
from fastapi.middleware.cors import CORSMiddleware

from .database import get_connection, init_database
from .schemas import ExportData, Insights, Period, PeriodCreate, PeriodUpdate
from .services import calculate_insights, row_to_period, utc_now


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


@app.get("/api/periods", response_model=List[Period])
def list_periods(connection: sqlite3.Connection = Depends(get_connection)) -> List[Period]:
    rows = connection.execute(
        "SELECT * FROM periods ORDER BY start_date DESC"
    ).fetchall()
    return [row_to_period(row) for row in rows]


@app.post("/api/periods", response_model=Period, status_code=status.HTTP_201_CREATED)
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


@app.put("/api/periods/{period_id}", response_model=Period)
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


@app.delete("/api/periods/{period_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_period(
    period_id: int,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Response:
    cursor = connection.execute("DELETE FROM periods WHERE id = ?", (period_id,))
    connection.commit()
    if cursor.rowcount == 0:
        raise HTTPException(status_code=404, detail="Kayıt bulunamadı.")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/api/insights", response_model=Insights)
def insights(
    today: date = None,
    connection: sqlite3.Connection = Depends(get_connection),
) -> Insights:
    rows = connection.execute("SELECT * FROM periods ORDER BY start_date").fetchall()
    periods = [row_to_period(row) for row in rows]
    return calculate_insights(periods, today or date.today())


@app.get("/api/export", response_model=ExportData)
def export_data(
    connection: sqlite3.Connection = Depends(get_connection),
) -> ExportData:
    rows = connection.execute(
        "SELECT * FROM periods ORDER BY start_date"
    ).fetchall()
    return ExportData(
        exported_at=utc_now(),
        periods=[row_to_period(row) for row in rows],
    )

