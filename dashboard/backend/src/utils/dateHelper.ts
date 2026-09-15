import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { formatInTimeZone, fromZonedTime } from "date-fns-tz";

export const MARKET_CALENDAR: {
  timezone: string;
  open: string;
  close: string;
  intervalMinutes: number;
  firstScrapeDelayMinutes: number;
  deliveryGraceSeconds: number;
  weekendDays: number[];
  fixedHolidays: string[];
  easterHolidays: { offsetDays: number; throughYear?: number }[];
} = JSON.parse(readFileSync(resolve(__dirname, "../../../../market-calendar.json"), "utf8"));

const DAY = 86_400_000;
const INTERVAL = MARKET_CALENDAR.intervalMinutes * 60_000;
const GRACE = MARKET_CALENDAR.deliveryGraceSeconds * 1000;

function shiftDay(day: string, offset: number): string {
  return new Date(Date.parse(day) + offset * DAY).toISOString().slice(0, 10);
}

export function isTradingDay(day: string): boolean {
  if (MARKET_CALENDAR.weekendDays.includes(new Date(day).getUTCDay()) ||
      MARKET_CALENDAR.fixedHolidays.includes(day.slice(5))) return false;

  // Gregorian Easter (Meeus/Jones/Butcher), matching Python dateutil.easter.
  const year = Number(day.slice(0, 4));
  const a = year % 19, b = Math.floor(year / 100), c = year % 100;
  const d = Math.floor(b / 4), e = b % 4;
  const f = Math.floor((b + 8) / 25), g = Math.floor((b - f + 1) / 3);
  const h = (19 * a + b - d - g + 15) % 30;
  const i = Math.floor(c / 4), k = c % 4;
  const l = (32 + 2 * e + 2 * i - h - k) % 7;
  const m = Math.floor((a + 11 * h + 22 * l) / 451);
  const month = Math.floor((h + l - 7 * m + 114) / 31);
  const date = (h + l - 7 * m + 114) % 31 + 1;
  const easter = Date.UTC(year, month - 1, date);
  return !MARKET_CALENDAR.easterHolidays.some(rule =>
    (rule.throughYear === undefined || year <= rule.throughYear) &&
    Date.parse(day) === easter + rule.offsetDays * DAY);
}

/** One trading day's observations, with deadlines separate from market opening hours. */
export function getMarketWindow(now = new Date()): {
  tradingDate: string;
  open: Date;
  close: Date;
  marketOpen: boolean;
  requiredSlot: Date | null;
  refreshAt: Date;
} {
  const today = formatInTimeZone(now, MARKET_CALENDAR.timezone, "yyyy-MM-dd");
  const at = (day: string, time: string) =>
    fromZonedTime(`${day}T${time}:00`, MARKET_CALENDAR.timezone);
  let tradingDate = today;
  if (now < at(today, MARKET_CALENDAR.open)) tradingDate = shiftDay(tradingDate, -1);
  while (!isTradingDay(tradingDate)) tradingDate = shiftDay(tradingDate, -1);
  const open = at(tradingDate, MARKET_CALENDAR.open);
  const close = at(tradingDate, MARKET_CALENDAR.close);
  const firstDeadline = open.getTime() + MARKET_CALENDAR.firstScrapeDelayMinutes * 60_000 + GRACE;
  let requiredSlot: Date | null = null;
  let nextDeadline = firstDeadline;
  if (now.getTime() >= firstDeadline) {
    const elapsed = Math.floor((now.getTime() - GRACE - open.getTime()) / INTERVAL);
    requiredSlot = new Date(Math.min(close.getTime(), open.getTime() + elapsed * INTERVAL));
    nextDeadline = requiredSlot.getTime() < close.getTime()
      ? requiredSlot.getTime() + INTERVAL + GRACE : Infinity;
  }
  let nextDay = shiftDay(tradingDate, 1);
  while (!isTradingDay(nextDay)) nextDay = shiftDay(nextDay, 1);
  const marketOpen = now >= open && now < close;
  const transition = marketOpen ? close : at(nextDay, MARKET_CALENDAR.open);
  return {
    tradingDate, open, close, marketOpen, requiredSlot,
    refreshAt: new Date(Math.min(now.getTime() + 60_000, transition.getTime(), nextDeadline)),
  };
}

/** Chart window uses the same trading day as status. */
export function getActiveTimeRange(now?: Date): [Date, Date] {
  const { open, close } = getMarketWindow(now);
  return [open, close];
}
