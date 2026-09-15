import type { StatusSnapshot } from "../types";
import { getCopenhagenTzAbbreviation } from "../utils/timezone";

interface InstituteStatusPanelProps {
  snapshot: StatusSnapshot | null;
  loading: boolean;
  error: string;
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
    label: "Partial",
  },
  ExchangeClosed: {
    dot: "bg-slate-400",
    badge: "bg-slate-100 text-slate-600",
    label: "Closed",
  },
  Waiting: {
    dot: "bg-slate-400",
    badge: "bg-slate-100 text-slate-600",
    label: "Waiting",
  },
  Unavailable: {
    dot: "bg-slate-400",
    badge: "bg-slate-100 text-slate-600",
    label: "Unknown",
  },
};

function formatLastUpdate(value: string | null, inSidebar: boolean): string {
  const date = value ? new Date(value) : null;
  if (!date || Number.isNaN(date.getTime())) return "No data";
  const formatted = new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Copenhagen",
    ...(inSidebar ? {} : { day: "2-digit", month: "2-digit" } as const),
    hour: "2-digit",
    minute: "2-digit",
    hour12: false,
  }).format(date);

  return `${inSidebar ? "" : "Updated "}${formatted} ${getCopenhagenTzAbbreviation(date)}`;
}

export function InstituteStatusPanel({ snapshot, loading, error, inSidebar = false }: InstituteStatusPanelProps) {
  const unavailable = Boolean(error) || !snapshot;
  const liveLabel = unavailable ? "" : snapshot.market_open ? "Live" : "Closed";

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
          {unavailable && (
            <p role="status" className={`text-xs ${inSidebar ? "text-slate-400" : "text-slate-500"}`}>
              Status unavailable
            </p>
          )}
          {snapshot?.institutes.map((row) => {
            const dataStyle = STATUS_STYLES[row.status] ?? STATUS_STYLES.Unavailable;
            const style = unavailable ? STATUS_STYLES.Unavailable : liveLabel === "Closed" ? STATUS_STYLES.ExchangeClosed : dataStyle;
            const description = `${unavailable ? "Status unavailable. Last confirmed " : liveLabel === "Closed" ? "Market closed. " : ""}${snapshot.trading_date}: ${dataStyle.label}. ${row.detail}`;

            return (
              <div
                key={row.institute}
                className={
                  inSidebar
                    ? "group rounded-md border border-slate-700/80 bg-slate-800/80 px-2 py-1.5"
                    : "rounded-xl border border-slate-100 bg-slate-50/60 px-3 py-2"
                }
              >
                <div className="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-2">
                  <p
                    className={`min-w-0 truncate ${inSidebar ? "text-xs" : "text-sm"} font-medium ${inSidebar ? "text-slate-200" : "text-slate-700"}`}
                    title={row.institute}
                  >
                    {row.institute}
                  </p>
                  <span
                    className={`inline-flex min-h-5 items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-medium leading-none whitespace-nowrap ${style.badge}`}
                    title={description}
                    aria-label={description}
                  >
                    <span className={`h-1.5 w-1.5 rounded-full ${style.dot}`} />
                    {style.label}
                  </span>
                </div>
                <p
                  className={`mt-1 text-xs ${inSidebar ? "text-slate-400" : "text-slate-500"}`}
                >
                  {formatLastUpdate(row.last_data_time, inSidebar)}
                </p>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
