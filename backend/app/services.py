import json
import statistics
from datetime import date, datetime, timedelta
from sqlite3 import Row
from typing import Iterable, List, Optional

from .schemas import Insights, Period, Profile


def row_to_period(row: Row) -> Period:
    values = dict(row)
    values["symptoms"] = json.loads(values["symptoms"] or "[]")
    return Period(**values)


def row_to_profile(row: Optional[Row]) -> Optional[Profile]:
    if row is None:
        return None
    values = dict(row)
    values.pop("id", None)
    return Profile(**values)


def calculate_insights(
    periods: Iterable[Period],
    today: date,
    default_cycle_length: int = 28,
    default_period_length: int = 5,
) -> Insights:
    ordered: List[Period] = sorted(periods, key=lambda item: item.start_date)

    cycle_lengths = [
        (current.start_date - previous.start_date).days
        for previous, current in zip(ordered, ordered[1:])
        if 15 <= (current.start_date - previous.start_date).days <= 60
    ]
    period_lengths = [
        (item.end_date - item.start_date).days + 1
        for item in ordered
        if item.end_date is not None and item.notes != "Onboarding setup"
    ]

    average_cycle = (
        round(statistics.mean(cycle_lengths))
        if cycle_lengths
        else default_cycle_length
    )
    average_period = (
        round(statistics.mean(period_lengths))
        if period_lengths
        else default_period_length
    )
    variation = (
        round(statistics.pstdev(cycle_lengths)) if len(cycle_lengths) >= 2 else None
    )

    if ordered:
        next_start = ordered[-1].start_date + timedelta(days=average_cycle)
        while next_start < today:
            next_start += timedelta(days=average_cycle)
    else:
        next_start = today + timedelta(days=average_cycle)

    next_end = next_start + timedelta(days=average_period - 1)
    ovulation = next_start - timedelta(days=14)
    fertile_start = ovulation - timedelta(days=5)
    fertile_end = ovulation + timedelta(days=1)

    completed_cycles = len(cycle_lengths)
    confidence = "high" if completed_cycles >= 6 else "medium" if completed_cycles >= 3 else "low"

    return Insights(
        average_cycle_length=average_cycle,
        average_period_length=average_period,
        cycle_variation=variation,
        next_period_start=next_start,
        next_period_end=next_end,
        ovulation_date=ovulation,
        fertile_window_start=fertile_start,
        fertile_window_end=fertile_end,
        days_until_next_period=(next_start - today).days,
        completed_cycles=completed_cycles,
        confidence=confidence,
        is_estimate=completed_cycles < 3,
    )


def utc_now() -> datetime:
    return datetime.utcnow()
