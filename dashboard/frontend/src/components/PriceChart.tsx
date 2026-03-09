import { useMemo } from "react";
import Plot from "react-plotly.js";
import type { SpotPrice, MasterData, FilterState, FilterKey } from "../types";
import { colorGradient } from "../utils/colors";
import { valuesMatch } from "../utils/filterValue";
import { COPENHAGEN_TIMEZONE, getCopenhagenTzAbbreviation } from "../utils/timezone";

interface PriceChartProps {
  prices: SpotPrice[];
  masterData: MasterData[];
  filters: FilterState;
  dateRange: [string, string] | null;
  showHistoric: boolean;
}

interface MergedRow {
  timestamp: string;
  isin: string;
  spot_price: number;
  institute: string;
  coupon_rate: number;
  years_to_maturity: number;
  max_interest_only_period: number;
}

type GroupKey = string;


function toCopenhagenLocalTimestamp(timestamp: string): string {
  const date = new Date(timestamp);
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

  const getPart = (type: Intl.DateTimeFormatPartTypes) =>
    parts.find((part) => part.type === type)?.value;

  return `${getPart("year")}-${getPart("month")}-${getPart("day")}T${getPart("hour")}:${getPart("minute")}:${getPart("second")}`;
}

function toCopenhagenLocalMinuteTimestamp(timestamp: string): string {
  return toCopenhagenLocalTimestamp(timestamp).slice(0, 16);
}

function buildFiveMinuteSlots(startIso: string, endIso: string): string[] {
  const start = new Date(startIso);
  const end = new Date(endIso);

  if (Number.isNaN(start.getTime()) || Number.isNaN(end.getTime()) || start > end) {
    return [];
  }

  const roundedStart = new Date(start);
  roundedStart.setUTCSeconds(0, 0);
  const minuteOffset = roundedStart.getUTCMinutes() % 5;
  if (minuteOffset !== 0) {
    roundedStart.setUTCMinutes(roundedStart.getUTCMinutes() - minuteOffset);
  }

  const roundedEnd = new Date(end);
  roundedEnd.setUTCSeconds(0, 0);
  const endMinuteOffset = roundedEnd.getUTCMinutes() % 5;
  if (endMinuteOffset !== 0) {
    roundedEnd.setUTCMinutes(roundedEnd.getUTCMinutes() + (5 - endMinuteOffset));
  }

  const slots: string[] = [];
  for (
    let cursor = new Date(roundedStart);
    cursor <= roundedEnd;
    cursor = new Date(cursor.getTime() + 5 * 60 * 1000)
  ) {
    slots.push(cursor.toISOString());
  }

  return slots;
}

function formatGroupLabel(groupers: FilterKey[], values: (string | number)[]): string {
  return groupers
    .map((g, i) => `${g.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}: ${values[i]}`)
    .join("<br>");
}

function getGroupKey(row: MergedRow, groupers: FilterKey[]): GroupKey {
  return groupers.map((g) => String(row[g])).join("|");
}

export function PriceChart({
  prices,
  masterData,
  filters,
  dateRange,
  showHistoric,
}: PriceChartProps) {
  const { traces, layout } = useMemo(() => {
    // Step 1: Filter master data by selected filters
    let filteredMaster = masterData;
    const groupers: FilterKey[] = [];

    for (const key of Object.keys(filters) as FilterKey[]) {
      const selected = filters[key];
      if (selected.length > 0) {
        filteredMaster = filteredMaster.filter((row) =>
          valuesMatch(selected, row[key] as string | number)
        );
      }
      if (selected.length === 0 || selected.length > 1) {
        groupers.push(key);
      }
    }

    const validIsins = new Set(filteredMaster.map((m) => m.isin));

    // Step 2: Filter prices to matching ISINs
    const filteredPrices = prices.filter((p) => validIsins.has(p.isin));

    // Step 3: Merge prices with master data
    const masterMap = new Map(masterData.map((m) => [m.isin, m]));
    const merged: MergedRow[] = filteredPrices
      .map((p) => {
        const m = masterMap.get(p.isin);
        if (!m) return null;
        return { ...p, ...m };
      })
      .filter(Boolean) as MergedRow[];

    // Step 4: Group by groupers
    const groups = new Map<GroupKey, MergedRow[]>();
    for (const row of merged) {
      const key = groupers.length > 0 ? getGroupKey(row, groupers) : "";
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(row);
    }

    // Step 5: Sort groups by mean price (descending)
    const sortedGroups = [...groups.entries()].sort((a, b) => {
      const meanA =
        a[1].reduce((s, r) => s + r.spot_price, 0) / a[1].length;
      const meanB =
        b[1].reduce((s, r) => s + r.spot_price, 0) / b[1].length;
      return meanB - meanA;
    });

    // Step 6: Generate color gradient
    const colors = colorGradient(sortedGroups.length);

    // Step 7: Build Plotly traces
    const plotTraces: Plotly.Data[] = sortedGroups.map(
      ([key, rows], idx) => {
        // Sort by timestamp
        const sorted = [...rows].sort(
          (a, b) =>
            new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime()
        );

        // Deduplicate by timestamp per group
        const seen = new Set<string>();
        const deduped = sorted.filter((r) => {
          const ts = showHistoric
            ? r.timestamp.split("T")[0]
            : r.timestamp;
          if (seen.has(ts)) return false;
          seen.add(ts);
          return true;
        });

        const expectedSlots =
          !showHistoric && dateRange
            ? buildFiveMinuteSlots(dateRange[0], dateRange[1])
            : [];

        const slotPriceMap = new Map<string, number>();
        deduped.forEach((r) => {
          slotPriceMap.set(toCopenhagenLocalMinuteTimestamp(r.timestamp), r.spot_price);
        });

        const x = showHistoric
          ? deduped.map((r) => r.timestamp.split("T")[0])
          : (expectedSlots.length > 0 ? expectedSlots : deduped.map((r) => r.timestamp)).map((ts) =>
              toCopenhagenLocalMinuteTimestamp(ts)
            );

        const y = showHistoric
          ? deduped.map((r) => r.spot_price)
          : x.map((timeSlot) => slotPriceMap.get(timeSlot) ?? null);

        const groupValues = key
          ? key.split("|").map((v, i) => {
              const g = groupers[i];
              return g === "coupon_rate" ||
                g === "years_to_maturity" ||
                g === "max_interest_only_period"
                ? Number(v)
                : v;
            })
          : [];

        const name =
          groupers.length > 0 ? formatGroupLabel(groupers, groupValues) : "";

        return {
          type: "scattergl" as const,
          mode: "lines" as const,
          x,
          y,
          name,
          line: {
            width: 3,
            shape: (showHistoric ? "linear" : "hv") as "linear" | "hv",
            color: colors[idx],
          },
          hovertemplate: showHistoric
            ? `${name ? name + "<br>" : ""}Date: %{x}<br>Price: %{y:.2f}<extra></extra>`
            : `${name ? name + "<br>" : ""}Time: %{x}<br>Price: %{y:.2f}<extra></extra>`,
          connectgaps: showHistoric,
          showlegend: false,
        };
      }
    );

    // Compute timezone label
    const tzLabel = getCopenhagenTzAbbreviation();

    // Layout
    const localDateRange =
      !showHistoric && dateRange
        ? [
            toCopenhagenLocalTimestamp(dateRange[0]),
            toCopenhagenLocalTimestamp(dateRange[1]),
          ]
        : null;

    const plotLayout: Partial<Plotly.Layout> = {
      plot_bgcolor: "#f2f2f2",
      paper_bgcolor: "#ffffff",
      font: { color: "#000000", family: "Inter, system-ui, sans-serif" },
      margin: { l: 60, r: 30, t: 20, b: 50 },
      xaxis: {
        title: { text: showHistoric ? "Date" : `Time (${tzLabel})` },
        showline: true,
        zeroline: false,
        showgrid: true,
        gridcolor: "#d1d5db",
        fixedrange: !showHistoric,
        nticks: 9,
        ...(!showHistoric
          ? {
              tickformat: "%H:%M",
              dtick: 60 * 60 * 1000,
              minor: {
                showgrid: true,
                dtick: 15 * 60 * 1000,
                gridcolor: "#d1d5db",
                griddash: "dot",
              },
            }
          : {}),
        ...(!showHistoric && localDateRange
          ? { range: [localDateRange[0], localDateRange[1]] }
          : {}),
        ...(showHistoric
          ? {
              rangeselector: {
                buttons: [
                  { count: 1, label: "1m", step: "month", stepmode: "backward" },
                  { count: 6, label: "6m", step: "month", stepmode: "backward" },
                  { count: 1, label: "YTD", step: "year", stepmode: "todate" },
                  { count: 1, label: "1y", step: "year", stepmode: "backward" },
                  { step: "all" },
                ],
              },
              rangeslider: { visible: false },
            }
          : {}),
      },
      yaxis: {
        showgrid: true,
        showline: true,
        zeroline: false,
        gridcolor: "#d1d5db",
        fixedrange: showHistoric,
      },
      showlegend: false,
      autosize: true,
    };

    return { traces: plotTraces, layout: plotLayout };
  }, [prices, masterData, filters, dateRange, showHistoric]);

  return (
    <Plot
      data={traces}
      layout={layout}
      useResizeHandler
      style={{ width: "100%", height: "100%" }}
      config={{ displayModeBar: false, responsive: true }}
    />
  );
}
