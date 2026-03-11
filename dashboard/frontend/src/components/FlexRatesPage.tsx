import { useMemo, useState, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import Plot from "react-plotly.js";
import { MultiSelect } from "./MultiSelect";
import { useFlexRates } from "../hooks/useFlexRates";
import { useMasterDataFloat } from "../hooks/useMasterDataFloat";
import { colorGradient } from "../utils/colors";
import { valuesMatch } from "../utils/filterValue";

type FlexFilters = {
  institute: string[];
  fixed_rate_period: number[];
  max_interest_only_period: number[];
};

type FlexFilterKey = keyof FlexFilters;

function parseFilters(params: URLSearchParams): FlexFilters {
  return {
    institute: params.get("institute")?.split(",").filter(Boolean) ?? [],
    fixed_rate_period: params.get("fixed_rate_period")?.split(",").filter(Boolean).map(Number) ?? [],
    max_interest_only_period:
      params.get("max_interest_only_period")?.split(",").filter(Boolean).map(Number) ?? [],
  };
}

export function FlexRatesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<FlexFilters>(() => parseFilters(searchParams));
  const [filtersOpen, setFiltersOpen] = useState(false);
  const { rates, loading: ratesLoading } = useFlexRates();
  const { masterDataFloat, loading: masterLoading } = useMasterDataFloat();

  useEffect(() => {
    const params: Record<string, string> = {};
    (Object.keys(filters) as FlexFilterKey[]).forEach((key) => {
      if (filters[key].length > 0) params[key] = filters[key].join(",");
    });
    setSearchParams(params, { replace: true });
  }, [filters, setSearchParams]);

  const available = useMemo(() => {
    function filterByOthers(exclude: FlexFilterKey) {
      return masterDataFloat.filter((row) => {
        for (const key of Object.keys(filters) as FlexFilterKey[]) {
          if (key === exclude) continue;
          if (filters[key].length === 0) continue;
          if (!valuesMatch(filters[key], row[key] as string | number)) return false;
        }
        return true;
      });
    }

    return {
      institute: [...new Set(filterByOthers("institute").map((r) => r.institute))].sort(),
      fixed_rate_period: [...new Set(filterByOthers("fixed_rate_period").map((r) => r.fixed_rate_period))].sort(
        (a, b) => a - b
      ),
      max_interest_only_period: [
        ...new Set(filterByOthers("max_interest_only_period").map((r) => r.max_interest_only_period)),
      ].sort((a, b) => a - b),
    };
  }, [masterDataFloat, filters]);

  const traces = useMemo(() => {
    const filtered = rates.filter((row) => {
      return (Object.keys(filters) as FlexFilterKey[]).every((key) => {
        const selected = filters[key];
        return selected.length === 0 || valuesMatch(selected, row[key] as string | number);
      });
    });

    const groupers = (Object.keys(filters) as FlexFilterKey[]).filter(
      (key) => filters[key].length === 0 || filters[key].length > 1
    );

    const groups = new Map<string, typeof filtered>();
    filtered.forEach((row) => {
      const key = groupers.map((g) => String(row[g])).join("|");
      if (!groups.has(key)) groups.set(key, []);
      groups.get(key)!.push(row);
    });

    const sortedGroups = [...groups.entries()].sort(
      (a, b) => b[1].reduce((s, r) => s + r.spot_rate, 0) / b[1].length - a[1].reduce((s, r) => s + r.spot_rate, 0) / a[1].length
    );
    const colors = colorGradient(sortedGroups.length || 1);

    return sortedGroups.map(([key, rows], idx) => {
      const sorted = [...rows].sort((a, b) => new Date(a.timestamp).getTime() - new Date(b.timestamp).getTime());
      const label = key
        ? key
            .split("|")
            .map((v, i) => `${groupers[i].replace(/_/g, " ")}: ${v}`)
            .join("<br>")
        : "All";

      return {
        type: "scatter" as const,
        mode: "lines" as const,
        x: sorted.map((r) => r.timestamp.split("T")[0]),
        y: sorted.map((r) => r.spot_rate),
        line: { width: 3, color: colors[idx] },
        hovertemplate: `${label}<br>Date: %{x}<br>Rate: %{y:.2f}<extra></extra>`,
        showlegend: false,
      };
    });
  }, [rates, filters]);

  const activeFilterCount = (Object.values(filters) as (string | number)[][]).filter((v) => v.length > 0).length;

  return (
    <div className="flex h-full flex-col gap-4 lg:flex-row lg:gap-6">
      <button
        className="lg:hidden flex items-center gap-2 rounded-lg border border-gray-200 bg-white px-3 py-2 text-sm font-medium text-gray-700 shadow-sm"
        onClick={() => setFiltersOpen((prev) => !prev)}
      >
        <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z" />
        </svg>
        Filters
        {activeFilterCount > 0 && (
          <span className="rounded-full bg-blue-100 px-1.5 py-0.5 text-xs font-semibold text-blue-700">
            {activeFilterCount}
          </span>
        )}
      </button>

      <div className={`${filtersOpen ? "block" : "hidden"} lg:block w-full lg:w-72 lg:shrink-0`}>
        <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-5">
          <div className="flex flex-col gap-5">
            <MultiSelect
              label="Institute"
              options={available.institute.map((v) => ({ label: v, value: v }))}
              value={filters.institute}
              onChange={(v) => setFilters((prev) => ({ ...prev, institute: v as string[] }))}
            />
            <MultiSelect
              label="Fixed rate period"
              options={available.fixed_rate_period.map((v) => ({ label: String(v), value: v }))}
              value={filters.fixed_rate_period}
              onChange={(v) => setFilters((prev) => ({ ...prev, fixed_rate_period: v as number[] }))}
            />
            <MultiSelect
              label="Max interest-only period"
              options={available.max_interest_only_period.map((v) => ({ label: String(v), value: v }))}
              value={filters.max_interest_only_period}
              onChange={(v) => setFilters((prev) => ({ ...prev, max_interest_only_period: v as number[] }))}
            />
          </div>
        </div>
      </div>

      <div className="min-h-[58vh] min-w-0 flex-1 lg:min-h-0">
        <div className="h-full rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {ratesLoading || masterLoading ? (
            <div className="flex h-full min-h-[320px] items-center justify-center text-sm text-gray-400">Loading rates...</div>
          ) : (
            <Plot
              data={traces}
              layout={{
                plot_bgcolor: "#f2f2f2",
                paper_bgcolor: "#ffffff",
                margin: { l: 60, r: 30, t: 20, b: 50 },
                xaxis: { title: { text: "Date" }, showgrid: true, gridcolor: "#d1d5db", rangeselector: {
                  buttons: [
                    { count: 1, label: "1m", step: "month", stepmode: "backward" },
                    { count: 6, label: "6m", step: "month", stepmode: "backward" },
                    { count: 1, label: "YTD", step: "year", stepmode: "todate" },
                    { count: 1, label: "1y", step: "year", stepmode: "backward" },
                    { step: "all" },
                  ],
                } },
                yaxis: { showgrid: true, gridcolor: "#d1d5db" },
                autosize: true,
                showlegend: false,
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
