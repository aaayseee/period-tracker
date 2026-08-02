from datetime import date, datetime
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


FlowLevel = Literal["light", "medium", "heavy"]


class PeriodBase(BaseModel):
    start_date: date
    end_date: Optional[date] = None
    flow: FlowLevel = "medium"
    symptoms: List[str] = Field(default_factory=list, max_length=12)
    notes: str = Field(default="", max_length=1000)

    @model_validator(mode="after")
    def validate_date_range(self) -> "PeriodBase":
        if self.end_date and self.end_date < self.start_date:
            raise ValueError("Bitiş tarihi başlangıç tarihinden önce olamaz.")
        if self.end_date and (self.end_date - self.start_date).days > 14:
            raise ValueError("Regl süresi 15 günden uzun kaydedilemez.")
        return self


class PeriodCreate(PeriodBase):
    pass


class PeriodUpdate(PeriodBase):
    pass


class Period(PeriodBase):
    id: int
    created_at: datetime
    updated_at: datetime


class Insights(BaseModel):
    average_cycle_length: int
    average_period_length: int
    cycle_variation: Optional[int]
    next_period_start: date
    next_period_end: date
    ovulation_date: date
    fertile_window_start: date
    fertile_window_end: date
    days_until_next_period: int
    completed_cycles: int
    confidence: Literal["low", "medium", "high"]
    is_estimate: bool


class ExportData(BaseModel):
    exported_at: datetime
    periods: List[Period]

