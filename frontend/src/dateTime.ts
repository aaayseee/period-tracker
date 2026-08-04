const HAS_TIME_ZONE = /(?:Z|[+-]\d{2}:?\d{2})$/i;

/**
 * API timestamps are UTC. Legacy responses did not include a timezone suffix,
 * so keep parsing those values as UTC instead of browser-local time.
 */
export function parseApiDateTime(value: string): Date {
  const normalized = value.includes("T") ? value : value.replace(" ", "T");
  return new Date(HAS_TIME_ZONE.test(normalized) ? normalized : `${normalized}Z`);
}

export function formatApiDateTime(value: string): string {
  return parseApiDateTime(value).toLocaleString("tr-TR");
}

export function formatApiDate(value: string): string {
  return parseApiDateTime(value).toLocaleDateString("tr-TR");
}
