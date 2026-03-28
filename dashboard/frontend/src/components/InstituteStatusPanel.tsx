import type { InstituteStatus } from "../types";
import { getCopenhagenTzAbbreviation } from "../utils/timezone";

interface InstituteStatusPanelProps {
  status: InstituteStatus[];
  loading: boolean;
  inSidebar?: boolean;
}

const STATUS_STYLES: Record<string, { dot: string; badge: string; label: string }> = {
  OK: {
    dot: "bg-emerald-500",
    badge: "bg-emerald-100 text-emerald-700",
    label: "OK",
  },
  NotOK: {
    dot: "bg-rose-500",
    badge: "bg-rose-100 text-rose-700",
    label: "Not OK",
  },
  SomeDataMissing: {
    dot: "bg-amber-500",
    badge: "bg-amber-100 text-amber-700",
    label: "Some missing",
  },
  ExchangeClosed: {
    dot: "bg-slate-400",
    badge: "bg-slate-100 text-slate-600",
    label: "Closed",
  },
};

function formatLastUpdate(value: string): { formatted: string; timezone: "CET" | "CEST" } {
  const date = new Date(value);
  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    day: "2-digit",
    month: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);

  return { formatted, timezone: getCopenhagenTzAbbreviation(date) };
}

function formatSidebarLastUpdate(value: string): { formatted: string; timezone: "CET" | "CEST" } {
  const date = new Date(value);
  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);

  return { formatted, timezone: getCopenhagenTzAbbreviation(date) };
}

function getCopenhagenLiveLabel(): "Live" | "Closed" {
  const parts = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    weekday: "short",
    hour: "2-digit",
    hour12: false,
  }).formatToParts(new Date());

  const weekday = parts.find((part) => part.type === "weekday")?.value;
  const hourValue = parts.find((part) => part.type === "hour")?.value;
  const hour = hourValue ? Number.parseInt(hourValue, 10) : NaN;
  const isWeekday = weekday !== "Sat" && weekday !== "Sun";
  const isLiveHour = !Number.isNaN(hour) && hour >= 9 && hour < 17;

  return isWeekday && isLiveHour ? "Live" : "Closed";
}

export function InstituteStatusPanel({ status, loading, inSidebar = false }: InstituteStatusPanelProps) {
  const liveLabel = getCopenhagenLiveLabel();

  return (
    <div
      className={
        inSidebar
          ? "w-full rounded-lg border border-slate-700/80 bg-slate-900/60 p-2"
          : "rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      }
    >
      <div className={`flex items-center justify-between ${inSidebar ? "mb-2" : "mb-3"}`}>
        <h3 className={`${inSidebar ? "text-sm font-semibold" : "text-sm font-semibold"} ${inSidebar ? "text-slate-100" : "text-slate-800"}`}>
          Institute Status
        </h3>
        <span
          className={`${inSidebar ? "text-xs" : "text-xs"} font-semibold tracking-wide uppercase ${
            liveLabel === "Live" ? "text-emerald-300" : "text-slate-300"
          }`}
        >
          {liveLabel}
        </span>
      </div>

      {loading ? (
        <p className={`text-sm ${inSidebar ? "text-slate-400" : "text-slate-400"}`}>Loading status…</p>
      ) : (
        <div className={inSidebar ? "space-y-1.5" : "space-y-2"}>
          {status.map((row) => {
            const style = STATUS_STYLES[row.status] ?? {
              dot: "bg-slate-400",
              badge: "bg-slate-100 text-slate-600",
              label: row.status,
            };

            const lastUpdate = inSidebar
              ? formatSidebarLastUpdate(row.last_data_time)
              : formatLastUpdate(row.last_data_time);

            return (
              <div
                key={row.institute}
                className={
                  inSidebar
                    ? "group rounded-md border border-slate-700/80 bg-slate-800/80 px-2 py-1.5"
                    : "rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2"
                }
              >
                <div className={inSidebar ? "flex items-center justify-between gap-2" : "flex items-center gap-2"}>
                  <p className={`${inSidebar ? "text-xs" : "text-sm"} font-medium ${inSidebar ? "text-slate-200" : "text-slate-700"}`}>
                    {row.institute}
                  </p>
                  <span
                    className={`inline-flex min-h-5 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium leading-none whitespace-nowrap ${style.badge}`}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                    {style.label}
                  </span>
                </div>
                <p
                  className={`mt-1 text-xs ${inSidebar ? "text-slate-400" : "text-slate-500"}`}
                >
                  {inSidebar ? `${lastUpdate.formatted} ${lastUpdate.timezone}` : `Updated ${lastUpdate.formatted} ${lastUpdate.timezone}`}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
