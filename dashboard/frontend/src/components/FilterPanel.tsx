import { useMemo } from "react";
import { MultiSelect } from "./MultiSelect";
import type { MasterData, SpotPrice, FilterState, FilterKey } from "../types";
import { useFilterCascade } from "../hooks/useFilterCascade";

interface FilterPanelProps {
  masterData: MasterData[];
  prices: SpotPrice[];
  filters: FilterState;
  onFilterChange: (key: FilterKey, value: (string | number)[]) => void;
  showHistoric: boolean;
  onToggleHistoric: (on: boolean) => void;
}

export function FilterPanel({
  masterData,
  prices,
  filters,
  onFilterChange,
  showHistoric,
  onToggleHistoric,
}: FilterPanelProps) {
  // Only consider bonds that have price data in the current dataset
  const isinsWithPrices = useMemo(
    () => new Set(prices.map((p) => p.isin)),
    [prices]
  );

  const activeMasterData = useMemo(
    () => masterData.filter((m) => isinsWithPrices.has(m.isin)),
    [masterData, isinsWithPrices]
  );

  // Full cascade: for each dropdown, filter masterData by all OTHER selected filters
  // to determine that dropdown's available options.
  const availableOptions = useFilterCascade(activeMasterData, filters);

  return (
    <div className="flex flex-col gap-5">
      {/* Historic toggle */}
      <div className="flex items-center gap-3">
        <button
          onClick={() => onToggleHistoric(!showHistoric)}
          className={`relative inline-flex h-6 w-11 shrink-0 cursor-pointer rounded-full transition-colors duration-200 ${
            showHistoric ? "bg-emerald-500" : "bg-gray-300"
          }`}
        >
          <span
            className={`inline-block h-5 w-5 transform rounded-full bg-white shadow-sm transition-transform duration-200 ${
              showHistoric ? "translate-x-[22px]" : "translate-x-0.5"
            } mt-0.5`}
          />
        </button>
        <span className="text-sm font-medium text-gray-700">
          Show historic prices
        </span>
      </div>

      <MultiSelect
        label="Institute"
        options={availableOptions.institute.map((v) => ({
          label: v,
          value: v,
        }))}
        value={filters.institute}
        onChange={(v) => onFilterChange("institute", v)}
      />

      <MultiSelect
        label="Coupon"
        options={availableOptions.coupon_rate.map((v) => ({
          label: String(v),
          value: v,
        }))}
        value={filters.coupon_rate}
        onChange={(v) => onFilterChange("coupon_rate", v)}
      />

      <MultiSelect
        label="Years to maturity"
        options={availableOptions.years_to_maturity.map((v) => ({
          label: String(v),
          value: v,
        }))}
        value={filters.years_to_maturity}
        onChange={(v) => onFilterChange("years_to_maturity", v)}
      />

      <MultiSelect
        label="Max interest-only period"
        options={availableOptions.max_interest_only_period.map((v) => ({
          label: String(v),
          value: v,
        }))}
        value={filters.max_interest_only_period}
        onChange={(v) => onFilterChange("max_interest_only_period", v)}
      />

      <MultiSelect
        label="ISIN"
        options={availableOptions.isin.map((v) => ({
          label: v,
          value: v,
        }))}
        value={filters.isin}
        onChange={(v) => onFilterChange("isin", v)}
        searchable
      />
    </div>
  );
}
