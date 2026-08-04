from datetime import date, datetime
from typing import Dict, List, Literal, Optional

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


class ProfileSetup(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    last_period_start: date
    average_cycle_length: int = Field(default=28, ge=15, le=60)
    average_period_length: int = Field(default=5, ge=1, le=15)


class ProfileUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=60)
    average_cycle_length: int = Field(ge=15, le=60)
    average_period_length: int = Field(ge=1, le=15)


class AccountRegister(ProfileSetup):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)
    invite_code: str = Field(min_length=24, max_length=40)


class AccountLogin(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    password: str = Field(min_length=8, max_length=128)


class AuthSession(BaseModel):
    email: str
    role: Literal["admin", "user"]


class RegistrationResult(AuthSession):
    recovery_code: str


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)


class PasswordRecovery(BaseModel):
    email: str = Field(min_length=5, max_length=254)
    recovery_code: str = Field(min_length=16, max_length=32)
    new_password: str = Field(min_length=8, max_length=128)


class RecoveryCodeResult(BaseModel):
    recovery_code: str


class PasswordRecoveryResult(AuthSession):
    recovery_code: str


class AdminInviteCreate(BaseModel):
    expiry_days: int = Field(default=7, ge=1, le=365)
    max_uses: int = Field(default=1, ge=1, le=100)


class AdminInvite(BaseModel):
    id: int
    expires_at: datetime
    max_uses: int
    use_count: int
    revoked_at: Optional[datetime]
    created_at: datetime


class AdminInviteCreated(AdminInvite):
    invite_code: str


class AdminUser(BaseModel):
    id: int
    email: str
    role: Literal["admin", "user"]
    is_active: bool
    created_at: datetime
    updated_at: datetime


class AdminUserStatusUpdate(BaseModel):
    is_active: bool


class AdminAuditLog(BaseModel):
    id: int
    admin_email: str
    action: str
    target_type: Optional[str]
    target_id: Optional[int]
    details: Dict[str, object]
    created_at: datetime


class Profile(BaseModel):
    name: str
    average_cycle_length: int
    average_period_length: int
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
    pms_window_start: date
    pms_window_end: date
    days_until_next_period: int
    completed_cycles: int
    confidence: Literal["low", "medium", "high"]
    is_estimate: bool


class ExportData(BaseModel):
    exported_at: datetime
    profile: Optional[Profile] = None
    periods: List[Period] = Field(max_length=5000)
    schema_version: Literal[1] = 1


class RestoreRequest(BaseModel):
    backup: ExportData
    mode: Literal["replace", "merge"] = "replace"

    @model_validator(mode="after")
    def validate_backup(self) -> "RestoreRequest":
        if self.mode == "replace" and self.backup.profile is None:
            raise ValueError("Tam geri yükleme için yedekte profil bulunmalıdır.")

        start_dates = [period.start_date for period in self.backup.periods]
        if len(start_dates) != len(set(start_dates)):
            raise ValueError("Yedekte aynı başlangıç tarihine sahip birden fazla kayıt var.")
        return self


class RestoreResult(BaseModel):
    mode: Literal["replace", "merge"]
    imported_periods: int
    skipped_periods: int
    total_periods: int
    profile_restored: bool
