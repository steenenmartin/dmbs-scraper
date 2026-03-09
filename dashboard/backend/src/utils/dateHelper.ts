import { toZonedTime, fromZonedTime } from "date-fns-tz";

const TZ_CPH = "Europe/Copenhagen";

const HOLIDAYS_2026 = [
  "2026-01-01",
  "2026-04-02",
  "2026-04-03",
  "2026-04-06",
  "2026-05-14",
  "2026-05-15",
  "2026-06-05",
  "2026-12-24",
  "2026-12-25",
  "2026-12-31",
];

function dateToString(d: Date): string {
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
}

function isHoliday(date: Date): boolean {
  return HOLIDAYS_2026.includes(dateToString(date));
}

function skipHolidays(date: Date): Date {
  if (isHoliday(date)) {
    const prev = new Date(date);
    prev.setDate(prev.getDate() - 1);
    return skipHolidays(prev);
  }
  return date;
}

/**
 * Port of Python's get_active_time_range.
 * Returns [startUTC, endUTC] as ISO strings.
 *
 * The logic determines which trading window to show:
 * - Weekend → previous Friday 9-17 CET
 * - Weekday before 9 CET → previous day 9-17 CET
 * - Weekday 9-17 CET → live window (start = 24h ago, end = now, but force_9_17 overrides)
 * - Weekday after 17 CET → today 9-17 CET
 * - Holidays → skip backwards recursively
 *
 * force_9_17=true forces start/end to exactly 9:00-17:00 on the end date.
 */
export function getActiveTimeRange(
  nowUtc?: Date,
  force917 = false
): [Date, Date] {
  const now = nowUtc ?? new Date();

  // Convert to Copenhagen local time
  const cphNow = toZonedTime(now, TZ_CPH);
  const weekday = cphNow.getDay(); // 0=Sun, 1=Mon, ..., 6=Sat
  const hour = cphNow.getHours();
  const minute = cphNow.getMinutes();

  let startCph: Date;
  let endCph: Date;

  if (weekday === 0) {
    // Sunday → previous Friday 9-17
    endCph = new Date(
      cphNow.getFullYear(),
      cphNow.getMonth(),
      cphNow.getDate() - 2,
      17,
      0
    );
    startCph = new Date(endCph.getTime());
    startCph.setHours(startCph.getHours() - 8);
  } else if (weekday === 6) {
    // Saturday → previous Friday 9-17
    endCph = new Date(
      cphNow.getFullYear(),
      cphNow.getMonth(),
      cphNow.getDate() - 1,
      17,
      0
    );
    startCph = new Date(endCph.getTime());
    startCph.setHours(startCph.getHours() - 8);
  } else if (hour >= 9 && hour < 17) {
    // During trading hours
    const roundedMinute = minute - (minute % 5);
    endCph = new Date(
      cphNow.getFullYear(),
      cphNow.getMonth(),
      cphNow.getDate(),
      Math.min(hour, 17),
      roundedMinute
    );
    if (weekday === 1) {
      // Monday → start from 72h ago (Friday)
      startCph = new Date(endCph.getTime());
      startCph.setHours(startCph.getHours() - 72);
    } else {
      startCph = new Date(endCph.getTime());
      startCph.setHours(startCph.getHours() - 24);
    }
  } else if (hour < 9) {
    // Before market open
    if (weekday === 1) {
      // Monday before 9 → previous Friday
      endCph = new Date(
        cphNow.getFullYear(),
        cphNow.getMonth(),
        cphNow.getDate() - 3,
        17,
        0
      );
    } else {
      endCph = new Date(
        cphNow.getFullYear(),
        cphNow.getMonth(),
        cphNow.getDate() - 1,
        17,
        0
      );
    }
    startCph = new Date(endCph.getTime());
    startCph.setHours(startCph.getHours() - 8);
  } else {
    // After market close (hour >= 17)
    endCph = new Date(
      cphNow.getFullYear(),
      cphNow.getMonth(),
      cphNow.getDate(),
      17,
      0
    );
    startCph = new Date(endCph.getTime());
    startCph.setHours(startCph.getHours() - 8);
  }

  // Holiday check on end date
  if (isHoliday(endCph)) {
    const prevDay = new Date(endCph);
    prevDay.setDate(prevDay.getDate() - 1);
    prevDay.setHours(17, 0, 0, 0);
    const prevDayUtc = fromZonedTime(prevDay, TZ_CPH);
    return getActiveTimeRange(prevDayUtc, force917);
  }

  startCph = skipHolidays(startCph);

  if (force917) {
    startCph = new Date(
      endCph.getFullYear(),
      endCph.getMonth(),
      endCph.getDate(),
      9,
      0
    );
    endCph = new Date(
      endCph.getFullYear(),
      endCph.getMonth(),
      endCph.getDate(),
      17,
      0
    );
  }

  // Convert Copenhagen local times back to UTC
  const startUtc = fromZonedTime(startCph, TZ_CPH);
  const endUtc = fromZonedTime(endCph, TZ_CPH);

  return [startUtc, endUtc];
}
