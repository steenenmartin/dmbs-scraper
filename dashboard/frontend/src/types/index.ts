export interface SpotPrice {
  timestamp: string;
  isin: string;
  spot_price: number;
}

export interface MasterData {
  isin: string;
  institute: string;
  coupon_rate: number;
  years_to_maturity: number;
  max_interest_only_period: number;
}

export interface FilterState {
  institute: string[];
  coupon_rate: number[];
  years_to_maturity: number[];
  max_interest_only_period: number[];
  isin: string[];
}

export interface SpotPricesResponse {
  prices: SpotPrice[];
  dateRange: [string, string];
}

export type FilterKey = keyof FilterState;
