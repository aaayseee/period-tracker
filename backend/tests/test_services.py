from datetime import date, datetime
from typing import Optional

from app.schemas import Period
from app.services import calculate_insights


def period(period_id: int, start: str, end: Optional[str] = None) -> Period:
    return Period(
        id=period_id,
        start_date=date.fromisoformat(start),
        end_date=date.fromisoformat(end) if end else None,
        flow="medium",
        symptoms=[],
        notes="",
        created_at=datetime(2026, 1, 1),
        updated_at=datetime(2026, 1, 1),
    )


def test_irregular_cycles_use_personal_average():
    periods = [
        period(1, "2026-01-01", "2026-01-05"),
        period(2, "2026-01-28", "2026-02-01"),
        period(3, "2026-03-01", "2026-03-05"),
        period(4, "2026-03-30", "2026-04-03"),
    ]

    result = calculate_insights(periods, date(2026, 4, 1))

    assert result.average_cycle_length == 29
    assert result.cycle_variation == 2
    assert result.next_period_start == date(2026, 4, 28)
    assert result.completed_cycles == 3
    assert result.confidence == "medium"


def test_implausible_gap_is_excluded_from_average():
    periods = [
        period(1, "2026-01-01"),
        period(2, "2026-01-29"),
        period(3, "2026-04-15"),
    ]

    result = calculate_insights(periods, date(2026, 4, 16))

    assert result.average_cycle_length == 28
    assert result.completed_cycles == 1
    assert result.next_period_start == date(2026, 5, 13)


def test_profile_defaults_are_used_without_history():
    result = calculate_insights(
        [],
        date(2026, 8, 3),
        default_cycle_length=31,
        default_period_length=6,
    )

    assert result.average_cycle_length == 31
    assert result.average_period_length == 6
    assert result.next_period_start == date(2026, 9, 3)
    assert result.is_estimate is True
