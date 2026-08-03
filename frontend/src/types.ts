export type FlowLevel = "light" | "medium" | "heavy";

export interface Period {
  id: number;
  start_date: string;
  end_date: string | null;
  flow: FlowLevel;
  symptoms: string[];
  notes: string;
  created_at: string;
  updated_at: string;
}

export interface PeriodPayload {
  start_date: string;
  end_date: string | null;
  flow: FlowLevel;
  symptoms: string[];
  notes: string;
}

export interface Profile {
  name: string;
  average_cycle_length: number;
  average_period_length: number;
  created_at: string;
  updated_at: string;
}

export interface ProfileUpdatePayload {
  name: string;
  average_cycle_length: number;
  average_period_length: number;
}

export interface ProfileSetupPayload {
  name: string;
  last_period_start: string;
  average_cycle_length: number;
  average_period_length: number;
}

export interface AccountRegisterPayload extends ProfileSetupPayload {
  email: string;
  password: string;
  invite_code: string;
}

export interface AccountLoginPayload {
  email: string;
  password: string;
}

export interface AuthSession {
  email: string;
  role: "admin" | "user";
}

export interface RegistrationResult extends AuthSession {
  recovery_code: string;
}

export interface PasswordChangePayload {
  current_password: string;
  new_password: string;
}

export interface PasswordRecoveryPayload {
  email: string;
  recovery_code: string;
  new_password: string;
}

export interface PasswordRecoveryResult extends AuthSession {
  recovery_code: string;
}

export interface RecoveryCodeResult {
  recovery_code: string;
}

export interface AdminUser {
  id: number;
  email: string;
  role: "admin" | "user";
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface AdminInvite {
  id: number;
  expires_at: string;
  max_uses: number;
  use_count: number;
  revoked_at: string | null;
  created_at: string;
}

export interface AdminInviteCreated extends AdminInvite {
  invite_code: string;
}

export interface AdminInviteCreatePayload {
  expiry_days: number;
  max_uses: number;
}

export interface BackupData {
  schema_version?: 1;
  exported_at: string;
  profile: Profile | null;
  periods: Period[];
}

export type RestoreMode = "replace" | "merge";

export interface RestorePayload {
  backup: BackupData;
  mode: RestoreMode;
}

export interface RestoreResult {
  mode: RestoreMode;
  imported_periods: number;
  skipped_periods: number;
  total_periods: number;
  profile_restored: boolean;
}

export interface Insights {
  average_cycle_length: number;
  average_period_length: number;
  cycle_variation: number | null;
  next_period_start: string;
  next_period_end: string;
  ovulation_date: string;
  fertile_window_start: string;
  fertile_window_end: string;
  pms_window_start: string;
  pms_window_end: string;
  days_until_next_period: number;
  completed_cycles: number;
  confidence: "low" | "medium" | "high";
  is_estimate: boolean;
}
