import { Router } from "express";
import { query, type Query } from "../db.js";
import { getMarketWindow, MARKET_CALENDAR } from "../utils/dateHelper.js";

export const INSTITUTES = ["Jyske", "Nordea", "RealKreditDanmark", "TotalKredit"] as const;
type DataStatus = "OK" | "SomeDataMissing" | "NotOK" | "Waiting";
type Coverage = {
  institute: string;
  isin: string | null;
  last_data_time: string | Date;
  first_slot: string | Date | null;
  last_slot: string | Date | null;
  slots: string | number;
};

// One day's canonical slots only. Filter invalid values before collapsing identical
// duplicates; conflicting valid quotes cannot establish coverage for that key.
export const COVERAGE_SQL = `
  WITH valid_quotes AS (
    SELECT isin, timestamp
    FROM spot_prices
    WHERE timestamp BETWEEN $1::timestamp AND $2::timestamp
      AND isin ~ '^[A-Z]{2}[A-Z0-9]{9}[0-9]$'
      AND spot_price > 0 AND spot_price < 'Infinity'::double precision
      AND mod(extract(epoch FROM (timestamp - $1::timestamp)), $4::numeric) = 0
    GROUP BY isin, timestamp
    HAVING count(DISTINCT spot_price) = 1
  ), scoped_quotes AS (
    SELECT m.institute, p.isin, p.timestamp
    FROM valid_quotes p
    JOIN (SELECT DISTINCT institute, isin FROM master_data
          WHERE institute = ANY($5::text[])) m USING (isin)
  )
  SELECT institute, isin,
         max(timestamp) AT TIME ZONE 'UTC' AS last_data_time,
         (min(timestamp) FILTER (WHERE timestamp <= $3::timestamp)) AT TIME ZONE 'UTC' AS first_slot,
         (max(timestamp) FILTER (WHERE timestamp <= $3::timestamp)) AT TIME ZONE 'UTC' AS last_slot,
         count(DISTINCT timestamp) FILTER (WHERE timestamp <= $3::timestamp) AS slots
  FROM scoped_quotes
  GROUP BY GROUPING SETS ((institute, isin), (institute))
`;

export async function getStatus(now = new Date(), read: Query = query) {
  const window = getMarketWindow(now);
  const step = MARKET_CALENDAR.intervalMinutes * 60_000;
  const required = window.requiredSlot?.getTime();
  const expected = required === undefined ? 0 : (required - window.open.getTime()) / step + 1;
  const rows = await read<Coverage>(COVERAGE_SQL, [
    window.open.toISOString(),
    new Date(Math.min(now.getTime(), window.close.getTime())).toISOString(),
    window.requiredSlot?.toISOString() ?? null,
    step / 1000,
    [...INSTITUTES],
  ]);

  return {
    trading_date: window.tradingDate,
    market_open: window.marketOpen,
    checked_at: now.toISOString(),
    refresh_at: window.refreshAt.toISOString(),
    institutes: INSTITUTES.map(institute => {
      const summary = rows.find(row => row.institute === institute && row.isin === null);
      const last = summary ? new Date(summary.last_data_time).toISOString() : null;
      let status: DataStatus = last ? "OK" : "Waiting";
      let detail = last
        ? "All expected spot observations are available."
        : "Waiting for the first scheduled spot quotes.";

      if (required !== undefined) {
        if (!summary?.last_slot || new Date(summary.last_slot).getTime() !== required) {
          status = "NotOK";
          const time = new Intl.DateTimeFormat("en-GB", {
            timeZone: MARKET_CALENDAR.timezone, hour: "2-digit", minute: "2-digit", hour12: false,
          }).format(window.requiredSlot!);
          detail = `No valid spot quotes for the ${time} scrape.`;
        } else if (Number(summary.slots) < expected || rows.some(row =>
          row.institute === institute && row.isin !== null && row.first_slot !== null &&
          Number(row.slots) < (required - new Date(row.first_slot).getTime()) / step + 1
        )) {
          status = "SomeDataMissing";
          detail = "Spot observations are missing from this trading day's five-minute history.";
        }
      }

      return { institute, status, last_data_time: last, detail };
    }),
  };
}

const router = Router();
router.get("/status", async (_req, res) => {
  res.set("Cache-Control", "no-store");
  try {
    res.json(await getStatus());
  } catch (error) {
    console.error("Error fetching spot coverage:", error);
    res.status(500).json({ error: "Failed to fetch status" });
  }
});
export default router;
