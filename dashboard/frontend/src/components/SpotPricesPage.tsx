import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { FilterPanel } from "./FilterPanel";
import { PriceChart } from "./PriceChart";
import { useSpotPrices } from "../hooks/useSpotPrices";
import { useMasterData } from "../hooks/useMasterData";
import { useClosingPrices } from "../hooks/useClosingPrices";
import type { FilterState, FilterKey } from "../types";

const EMPTY_FILTERS: FilterState = {
  institute: [],
  coupon_rate: [],
  years_to_maturity: [],
  max_interest_only_period: [],
  isin: [],
};

function parseFiltersFromParams(params: URLSearchParams): FilterState {
  return {
    institute: params.get("institute")?.split(",").filter(Boolean) ?? [],
    coupon_rate:
      params
        .get("coupon_rate")
        ?.split(",")
        .filter(Boolean)
        .map(Number) ?? [],
    years_to_maturity:
      params
        .get("years_to_maturity")
        ?.split(",")
        .filter(Boolean)
        .map(Number) ?? [],
    max_interest_only_period:
      params
        .get("max_interest_only_period")
        ?.split(",")
        .filter(Boolean)
        .map(Number) ?? [],
    isin: params.get("isin")?.split(",").filter(Boolean) ?? [],
  };
}

function filtersToParams(filters: FilterState): Record<string, string> {
  const params: Record<string, string> = {};
  for (const [key, values] of Object.entries(filters)) {
    if (values.length > 0) {
      params[key] = values.join(",");
    }
  }
  return params;
}

export function SpotPricesPage() {
  const [searchParams, setSearchParams] = useSearchParams();
  const [filters, setFilters] = useState<FilterState>(() =>
    parseFiltersFromParams(searchParams)
  );
  const [showHistoric, setShowHistoric] = useState(
    searchParams.get("show_historic") === "true"
  );

  const { prices, dateRange, loading: pricesLoading } = useSpotPrices();
  const { masterData, loading: masterLoading } = useMasterData();
  const { closingPrices, loading: closingLoading, fetchClosingPrices } = useClosingPrices();

  // Fetch closing prices when historic mode is toggled on
  useEffect(() => {
    if (showHistoric) {
      fetchClosingPrices();
    }
  }, [showHistoric, fetchClosingPrices]);

  // Sync filters to URL
  useEffect(() => {
    const params = filtersToParams(filters);
    if (showHistoric) params.show_historic = "true";
    setSearchParams(params, { replace: true });
  }, [filters, showHistoric, setSearchParams]);

  const handleFilterChange = useCallback(
    (key: FilterKey, value: (string | number)[]) => {
      setFilters((prev) => ({ ...prev, [key]: value }));
    },
    []
  );

  const isLoading =
    pricesLoading || masterLoading || (showHistoric && closingLoading);

  const activePrices =
    showHistoric && closingPrices ? closingPrices : prices;

  return (
    <div className="flex h-full gap-6">
      {/* Filter Panel */}
      <div className="w-64 shrink-0">
        <div className="rounded-xl bg-white p-5 shadow-sm border border-gray-100">
          <FilterPanel
            masterData={masterData}
            filters={filters}
            onFilterChange={handleFilterChange}
            showHistoric={showHistoric}
            onToggleHistoric={setShowHistoric}
          />
        </div>
      </div>

      {/* Chart */}
      <div className="flex-1 min-w-0">
        <div className="h-full rounded-xl bg-white shadow-sm border border-gray-100 overflow-hidden">
          {isLoading ? (
            <div className="flex h-full items-center justify-center">
              <div className="flex flex-col items-center gap-3">
                <div className="h-8 w-8 animate-spin rounded-full border-2 border-gray-200 border-t-blue-500" />
                <span className="text-sm text-gray-400">Loading prices...</span>
              </div>
            </div>
          ) : (
            <PriceChart
              prices={activePrices}
              masterData={masterData}
              filters={filters}
              dateRange={dateRange}
              showHistoric={showHistoric}
            />
          )}
        </div>
      </div>
    </div>
  );
}
