import { useMemo } from "react";
import type { MasterData, FilterState, FilterKey } from "../types";
import { valuesMatch } from "../utils/filterValue";

export function useFilterCascade(masterData: MasterData[], filters: FilterState) {
  return useMemo(() => {
    const keys = Object.keys(filters) as FilterKey[];

    function filterByOthers(excludeKey: FilterKey): MasterData[] {
      return masterData.filter((row) =>
        keys.every((key) => {
          if (key === excludeKey) return true;
          const selected = filters[key];
          if (selected.length === 0) return true;
          return valuesMatch(selected, row[key] as string | number);
        })
      );
    }

    return {
      institute: [...new Set(filterByOthers("institute").map((r) => r.institute))].sort(),
      coupon_rate: [...new Set(filterByOthers("coupon_rate").map((r) => r.coupon_rate))].sort((a, b) => a - b),
      years_to_maturity: [...new Set(filterByOthers("years_to_maturity").map((r) => r.years_to_maturity))].sort((a, b) => a - b),
      max_interest_only_period: [...new Set(filterByOthers("max_interest_only_period").map((r) => r.max_interest_only_period))].sort((a, b) => a - b),
      isin: [...new Set(filterByOthers("isin").map((r) => r.isin))].sort(),
    };
  }, [masterData, filters]);
}
