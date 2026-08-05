import type {
  AccountLoginPayload,
  AccountRegisterPayload,
  AdminAuditLog,
  AdminInvite,
  AdminInviteCreated,
  AdminInviteCreatePayload,
  AdminUser,
  AuthSession,
  BackupData,
  Insights,
  NotificationActionResult,
  NotificationConfig,
  NotificationPreferences,
  Period,
  PeriodPayload,
  PasswordChangePayload,
  PasswordRecoveryPayload,
  PasswordRecoveryResult,
  Profile,
  ProfileUpdatePayload,
  PushSubscriptionPayload,
  RecoveryCodeResult,
  RegistrationResult,
  RestorePayload,
  RestoreResult
} from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    credentials: "same-origin",
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    }
  });

  if (!response.ok) {
    let message = "Bir şeyler ters gitti.";
    try {
      const error: unknown = await response.json();
      if (typeof error === "object" && error !== null && "detail" in error) {
        const detail = (error as { detail: unknown }).detail;
        if (typeof detail === "string") {
          message = detail;
        } else if (Array.isArray(detail)) {
          const validationMessages = detail
            .map((item) => (
              typeof item === "object" && item !== null && "msg" in item
                ? String((item as { msg: unknown }).msg)
                : ""
            ))
            .filter(Boolean);
          if (validationMessages.length) message = validationMessages.join(" ");
        }
      }
    } catch {
      // The fallback message is enough for non-JSON server errors.
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  getSession: () => request<AuthSession | null>("/api/auth/session"),
  register: (payload: AccountRegisterPayload) =>
    request<RegistrationResult>("/api/auth/register", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  login: (payload: AccountLoginPayload) =>
    request<AuthSession>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  recoverPassword: (payload: PasswordRecoveryPayload) =>
    request<PasswordRecoveryResult>("/api/auth/recover", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  changePassword: (payload: PasswordChangePayload) =>
    request<AuthSession>("/api/auth/change-password", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  rotateRecoveryCode: () =>
    request<RecoveryCodeResult>("/api/auth/recovery-code", { method: "POST" }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),
  getAdminUsers: () => request<AdminUser[]>("/api/admin/users"),
  updateAdminUser: (id: number, isActive: boolean) =>
    request<AdminUser>(`/api/admin/users/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ is_active: isActive })
    }),
  getAdminInvites: () => request<AdminInvite[]>("/api/admin/invites"),
  createAdminInvite: (payload: AdminInviteCreatePayload) =>
    request<AdminInviteCreated>("/api/admin/invites", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  revokeAdminInvite: (id: number) =>
    request<AdminInvite>(`/api/admin/invites/${id}/revoke`, { method: "POST" }),
  getAdminAuditLogs: (limit = 50) =>
    request<AdminAuditLog[]>(`/api/admin/audit-logs?limit=${limit}`),
  getProfile: () => request<Profile | null>("/api/profile"),
  updateProfile: (payload: ProfileUpdatePayload) =>
    request<Profile>("/api/profile", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  getPeriods: () => request<Period[]>("/api/periods"),
  getInsights: () => request<Insights>("/api/insights"),
  getNotificationConfig: () => request<NotificationConfig>("/api/notifications/config"),
  updateNotificationPreferences: (payload: NotificationPreferences) =>
    request<NotificationPreferences>("/api/notifications/preferences", {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  savePushSubscription: (payload: PushSubscriptionPayload) =>
    request<{ status: string }>("/api/notifications/subscriptions", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  removePushSubscription: (endpoint: string) =>
    request<void>("/api/notifications/unsubscribe", {
      method: "POST",
      body: JSON.stringify({ endpoint })
    }),
  testNotification: () =>
    request<NotificationActionResult>("/api/notifications/test", { method: "POST" }),
  createPeriod: (payload: PeriodPayload) =>
    request<Period>("/api/periods", { method: "POST", body: JSON.stringify(payload) }),
  updatePeriod: (id: number, payload: PeriodPayload) =>
    request<Period>(`/api/periods/${id}`, {
      method: "PUT",
      body: JSON.stringify(payload)
    }),
  deletePeriod: (id: number) => request<void>(`/api/periods/${id}`, { method: "DELETE" }),
  restoreBackup: (payload: RestorePayload) =>
    request<RestoreResult>("/api/restore", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  getBackup: () => request<BackupData>("/api/export"),
  exportUrl: "/api/export"
};
