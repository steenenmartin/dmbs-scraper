import { useEffect, useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { Plot } from "../utils/plotly-instance";
import { MultiSelect } from "./MultiSelect";
import { useMasterData } from "../hooks/useMasterData";
import { useOHLCPrices } from "../hooks/useOHLCPrices";
import { useFilterCascade } from "../hooks/useFilterCascade";
import type { FilterState } from "../types";

type OhlcFilters = {
  institute: string[];
  coupon_rate: number[];
  years_to_maturity: number[];
  max_interest_only_period: number[];
  isin: string[];
};

type OhlcFilterKey = keyof OhlcFilters;

function parseFilters(params: URLSearchParams): OhlcFilters {
  return {
    institute: params.get("institute")?.split(",").filter(Boolean) ?? [],
    coupon_rate: params.get("coupon_rate")?.split(",").filter(Boolean).map(Number) ?? [],
    years_to_maturity: params.get("years_to_maturity")?.split(",").filter(Boolean).map(Number) ?? [],
    max_interest_only_period:
      params.get("max_interest_only_period")?.split(",").filter(Boolean).map(Number) ?? [],
    isin: params.get("isin")?.split(",").filter(Boolean) ?? [],
  };
}

export function OhlcPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<OhlcFilters>(() => parseFilters(searchParams));
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { masterData, loading: masterLoading } = useMasterData();
  const { ohlcPrices, loading: ohlcLoading } = useOHLCPrices();

  useEffect(() => {
    const params: Record<string, string> = {};
    (Object.keys(filters) as OhlcFilterKey[]).forEach((key) => {
      if (filters[key].length > 0) params[key] = filters[key].join(",");
    });
    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  const available = useFilterCascade(masterData, filters as FilterState);

  useEffect(() => {
    setFilters((prev) => {
      const nextIsin = prev.isin.filter((i) => available.isin.includes(i));
      if (nextIsin.length === prev.isin.length && nextIsin.every((v, i) => v === prev.isin[i])) {
        return prev;
      }
      return { ...prev, isin: nextIsin };
    });
  }, [available.isin]);

  const traces = useMemo<Plotly.Data[]>(() => {
    if (filters.isin.length === 0) return [];

    return filters.isin.flatMap((isin, idx) => {
      const series = ohlcPrices
        .filter((r) => r.isin === isin)
        .sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());

      if (series.length === 0) return [];

      const x = series.map((r) => r.timestamp.split("T")[0]);
      const close = series.map((r) => r.close_price);

      return [
        {
          type: "candlestick" as const,
          name: `${isin} OHLC`,
          x,
          open: series.map((r) => r.open_price),
          high: series.map((r) => r.high_price),
          low: series.map((r) => r.low_price),
          close,
          increasing: { line: { color: "#16a34a" } },
          decreasing: { line: { color: "#dc2626" } },
          opacity: filters.isin.length > 1 ? 0.55 : 1,
          showlegend: filters.isin.length > 1,
        },
        {
          type: "scatter" as const,
          mode: "lines" as const,
          name: `${isin} close`,
          x,
          y: close,
          line: { width: 1, color: ["#991b1b", "#1d4ed8", "#7c3aed", "#0f766e"][idx % 4] },
          hoverinfo: "skip" as const,
          showlegend: false,
        },
      ];
    });
  }, [ohlcPrices, filters.isin]);

  const activeFilterCount = (Object.values(filters) as (string | number)[][]).filter((v) => v.length > 0).length;

  return (
    <div className="flex h-full flex-col gap-4 lg:flex-row lg:gap-6">
      <div className="w-full lg:w-72 lg:shrink-0">
        <div className="rounded-2xl border border-gray-100 bg-white shadow-sm">
          <button
            className="lg:hidden w-full flex items-center justify-between px-4 py-3"
            onClick={() => setFiltersOpen((prev) => !prev)}
          >
            <span className="flex items-center gap-2 text-sm font-medium text-gray-700">
              Filters
              {activeFilterCount > 0 && (
                <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-xs font-semibold text-blue-700">
                  {activeFilterCount}
                </span>
              )}
            </span>
            <svg
              className={`h-4 w-4 text-gray-500 transition-transform duration-200 ${filtersOpen ? "rotate-180" : ""}`}
              fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
            >
              <path strokeLinecap="round" strokeLinejoin="round" d="M19 9l-7 7-7-7" />
            </svg>
          </button>
          <div className={`${filtersOpen ? "block" : "hidden"} lg:block p-4 sm:p-5`}>
          <div className="flex flex-col gap-5">
            <MultiSelect
              label="Institute"
              options={available.institute.map((v) => ({ label: v, value: v }))}
              value={filters.institute}
              onChange={(v) => setFilters((prev) => ({ ...prev, institute: v as string[] }))}
            />
            <MultiSelect
              label="Coupon"
              options={available.coupon_rate.map((v) => ({ label: String(v), value: v }))}
              value={filters.coupon_rate}
              onChange={(v) => setFilters((prev) => ({ ...prev, coupon_rate: v as number[] }))}
            />
            <MultiSelect
              label="Years to maturity"
              options={available.years_to_maturity.map((v) => ({ label: String(v), value: v }))}
              value={filters.years_to_maturity}
              onChange={(v) => setFilters((prev) => ({ ...prev, years_to_maturity: v as number[] }))}
            />
            <MultiSelect
              label="Max interest-only period"
              options={available.max_interest_only_period.map((v) => ({ label: String(v), value: v }))}
              value={filters.max_interest_only_period}
              onChange={(v) => setFilters((prev) => ({ ...prev, max_interest_only_period: v as number[] }))}
            />
            <MultiSelect
              label="ISIN"
              options={available.isin.map((v) => ({ label: v, value: v }))}
              value={filters.isin}
              onChange={(v) => setFilters((prev) => ({ ...prev, isin: v as string[] }))}
              searchable
              placeholder="Select ISIN(s) to plot"
            />
          </div>
          </div>
        </div>
      </div>

      <div className="min-h-[58vh] min-w-0 flex-1 lg:min-h-0">
        <div className="h-full rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {masterLoading || ohlcLoading ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-gray-400">Loading OHLC data...</div>
          ) : traces.length === 0 ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-gray-400">
              Select one or more ISINs to show OHLC prices.
            </div>
          ) : (
            <Plot
              data={traces}
              layout={{
                plot_bgcolor: "#f2f2f2",
                paper_bgcolor: "#ffffff",
                margin: { l: 60, r: 30, t: 20, b: 50 },
                xaxis: {
                  title: { text: "Date" },
                  showgrid: true,
                  gridcolor: "#d1d5db",
                  rangeslider: { visible: false },
                  rangeselector: {
                    buttons: [
                      { count: 1, label: "1m", step: "month", stepmode: "backward" },
                      { count: 6, label: "6m", step: "month", stepmode: "backward" },
                      { count: 1, label: "YTD", step: "year", stepmode: "todate" },
                      { count: 1, label: "1y", step: "year", stepmode: "backward" },
                      { step: "all" },
                    ],
                  },
                },
                yaxis: { showgrid: true, gridcolor: "#d1d5db" },
                autosize: true,
                showlegend: filters.isin.length > 1,
              }}
              useResizeHandler
              style={{ width: "100%", height: "100%" }}
              config={{ displayModeBar: false, responsive: true }}
            />
          )}
        </div>
      </div>
    </div>
  );
}
