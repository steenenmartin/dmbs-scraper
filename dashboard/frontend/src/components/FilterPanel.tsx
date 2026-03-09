import { useMemo } from "react";
import { MultiSelect } from "./MultiSelect";
import type { MasterData, FilterState, FilterKey } from "../types";

interface FilterPanelProps {
  masterData: MasterData[];
  filters: FilterState;
  onFilterChange: (key: FilterKey, value: (string | number)[]) => void;
  showHistoric: boolean;
  onToggleHistoric: (on: boolean) => void;
}

export function FilterPanel({
  masterData,
  filters,
  onFilterChange,
  showHistoric,
  onToggleHistoric,
}: FilterPanelProps) {
  // Full cascade: for each dropdown, filter masterData by all OTHER selected filters
  // to determine that dropdown's available options.
  const availableOptions = useMemo(() => {
    function filterByOthers(excludeKey: FilterKey): MasterData[] {
      return masterData.filter((row) => {
        for (const key of Object.keys(filters) as FilterKey[]) {
          if (key === excludeKey) continue;
          const selected = filters[key];
          if (selected.length === 0) continue;
          const rowVal = row[key];
          if (!selected.includes(rowVal as never)) return false;
        }
        return true;
      });
    }

    const forInstitute = filterByOthers("institute");
    const forCoupon = filterByOthers("coupon_rate");
    const forYtm = filterByOthers("years_to_maturity");
    const forMaxIo = filterByOthers("max_interest_only_period");
    const forIsin = filterByOthers("isin");

    return {
      institute: [...new Set(forInstitute.map((r) => r.institute))].sort(),
      coupon_rate: [...new Set(forCoupon.map((r) => r.coupon_rate))].sort(
        (a, b) => a - b
      ),
      years_to_maturity: [
        ...new Set(forYtm.map((r) => r.years_to_maturity)),
      ].sort((a, b) => a - b),
      max_interest_only_period: [
        ...new Set(forMaxIo.map((r) => r.max_interest_only_period)),
      ].sort((a, b) => a - b),
      isin: [...new Set(forIsin.map((r) => r.isin))].sort(),
    };
  }, [masterData, filters]);

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
