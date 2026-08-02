import type { Insights, Period, PeriodPayload } from "./types";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...options?.headers
    }
  });

  if (!response.ok) {
    let message = "Bir şeyler ters gitti.";
    try {
      const error = await response.json();
      message = typeof error.detail === "string" ? error.detail : message;
    } catch {
      // The fallback message is enough for non-JSON server errors.
    }
    throw new Error(message);
  }

  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const api = {
  getPeriods: () => request<Period[]>("/api/periods"),
  getInsights: () => request<Insights>("/api/insights"),
  createPeriod: (payload: PeriodPayload) =>
    request<Period>("/api/periods", { method: "POST", body: JSON.stringify(payload) }),
  deletePeriod: (id: number) => request<void>(`/api/periods/${id}`, { method: "DELETE" }),
  exportUrl: "/api/export"
};

