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
    label: "Exchange closed",
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

export function InstituteStatusPanel({ status, loading, inSidebar = false }: InstituteStatusPanelProps) {
  return (
    <div
      className={
        inSidebar
          ? "mx-3 mb-4 rounded-xl border border-slate-700 bg-slate-900/50 p-3"
          : "rounded-2xl border border-slate-200 bg-white p-4 shadow-sm"
      }
    >
      <div className="mb-3 flex items-center justify-between">
        <h3 className={`text-sm font-semibold ${inSidebar ? "text-slate-100" : "text-slate-800"}`}>
          Institute Status
        </h3>
        <span className={`text-xs ${inSidebar ? "text-slate-400" : "text-slate-400"}`}>Live</span>
      </div>

      {loading ? (
        <p className={`text-sm ${inSidebar ? "text-slate-400" : "text-slate-400"}`}>Loading status…</p>
      ) : (
        <div className="space-y-2">
          {status.map((row) => {
            const style = STATUS_STYLES[row.status] ?? {
              dot: "bg-slate-400",
              badge: "bg-slate-100 text-slate-600",
              label: row.status,
            };

            const lastUpdate = formatLastUpdate(row.last_data_time);

            return (
              <div
                key={row.institute}
                className={
                  inSidebar
                    ? "rounded-lg border border-slate-700 bg-slate-800/80 px-2.5 py-2"
                    : "rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2"
                }
              >
                <div className="flex items-center gap-2">
                  <span className={`h-2.5 w-2.5 rounded-full ${style.dot}`} />
                  <p className={`text-sm font-medium ${inSidebar ? "text-slate-200" : "text-slate-700"}`}>
                    {row.institute}
                  </p>
                </div>
                <p className={`mt-1.5 text-xs ${inSidebar ? "text-slate-400" : "text-slate-500"}`}>
                  Updated {lastUpdate.formatted} {lastUpdate.timezone}
                </p>
                <div className="mt-2">
                  <span
                    className={`inline-flex min-h-6 items-center justify-center rounded-full px-2.5 py-1 text-center text-[11px] font-medium leading-none whitespace-nowrap ${style.badge}`}
                  >
                    {style.label}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
