import { useState, useCallback, useEffect } from "react";
import { useSearchParams } from "react-router-dom";
import { FilterPanel } from "./FilterPanel";
import { PriceChart } from "./PriceChart";
import { useSpotPrices } from "../hooks/useSpotPrices";
import { useMasterData } from "../hooks/useMasterData";
import { useClosingPrices } from "../hooks/useClosingPrices";
import type { FilterState, FilterKey } from "../types";


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

  useEffect(() => {
    if (showHistoric) {
      fetchClosingPrices();
    }
  }, [showHistoric, fetchClosingPrices]);

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
    <div className="flex h-full flex-col gap-4 lg:flex-row lg:gap-6">
      <div className="w-full lg:w-72 lg:shrink-0">
        <div className="rounded-2xl border border-gray-100 bg-white p-4 shadow-sm sm:p-5">
          <FilterPanel
            masterData={masterData}
            prices={activePrices}
            filters={filters}
            onFilterChange={handleFilterChange}
            showHistoric={showHistoric}
            onToggleHistoric={setShowHistoric}
          />
        </div>
      </div>

      <div className="min-h-[58vh] min-w-0 flex-1 lg:min-h-0">
        <div className="h-full rounded-2xl border border-gray-100 bg-white shadow-sm overflow-hidden">
          {isLoading ? (
            <div className="flex h-full min-h-[320px] items-center justify-center">
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
