import pandas as pd
import datetime as dt
from .fixed_rate_bond_data_entry import FixedRateBondDataEntry


class FixedRateBondData:
    def __init__(self, fixed_rate_bond_data_entries: list[FixedRateBondDataEntry]):
        self.fixed_rate_bond_data_entries = fixed_rate_bond_data_entries

    def to_master_data_frame(self) -> pd.DataFrame:
        df = self.to_data_frame()
        return df[["isin", "institute", "years_to_maturity", "max_interest_only_period", "coupon_rate"]]

    def to_spot_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        return df[["timestamp", "isin", "spot_price"]]

    def to_offer_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        return df[["timestamp", "isin", "offer_price"]]

    def to_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = pd.DataFrame(x.__dict__ for x in self.fixed_rate_bond_data_entries)
        if scrape_time is not None:
            df.insert(0, "timestamp", scrape_time)

        return df
