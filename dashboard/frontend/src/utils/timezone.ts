const COPENHAGEN_TIMEZONE = "Europe/Copenhagen";

function getPart(parts: Intl.DateTimeFormatPart[], type: Intl.DateTimeFormatPartTypes): string {
  return parts.find((part) => part.type === type)?.value ?? "00";
}

function getCopenhagenOffsetMinutes(date: Date): number {
  const parts = new Intl.DateTimeFormat("sv-SE", {
    timeZone: COPENHAGEN_TIMEZONE,
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
    hour12: false,
  }).formatToParts(date);

  const copenhagenUtcMs = Date.UTC(
    Number(getPart(parts, "year")),
    Number(getPart(parts, "month")) - 1,
    Number(getPart(parts, "day")),
    Number(getPart(parts, "hour")),
    Number(getPart(parts, "minute")),
    Number(getPart(parts, "second"))
  );

  return Math.round((copenhagenUtcMs - date.getTime()) / 60_000);
}

// Cache keyed by UTC minute — DST transitions only happen on the hour
let tzCache: { minuteKey: number; result: "CET" | "CEST" } | null = null;

export function getCopenhagenTzAbbreviation(date: Date = new Date()): "CET" | "CEST" {
  const minuteKey = Math.floor(date.getTime() / 60_000);
  if (tzCache && tzCache.minuteKey === minuteKey) return tzCache.result;
  const result = getCopenhagenOffsetMinutes(date) >= 120 ? "CEST" : "CET";
  tzCache = { minuteKey, result };
  return result;
}

export { COPENHAGEN_TIMEZONE };
