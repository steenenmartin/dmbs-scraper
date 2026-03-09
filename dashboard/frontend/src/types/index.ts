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

export interface MasterDataFloat {
  institute: string;
  fixed_rate_period: number;
  max_interest_only_period: number;
}

export interface FlexRate {
  timestamp: string;
  institute: string;
  fixed_rate_period: number;
  max_interest_only_period: number;
  spot_rate: number;
}

export interface OHLCPrice {
  timestamp: string;
  isin: string;
  open_price: number;
  high_price: number;
  low_price: number;
  close_price: number;
}

export interface InstituteStatus {
  institute: string;
  last_data_time: string;
  status: "OK" | "NotOK" | "ExchangeClosed" | "SomeDataMissing" | string;
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
