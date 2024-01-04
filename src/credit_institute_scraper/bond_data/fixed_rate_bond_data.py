import pandas as pd
import datetime as dt

from .bond_data import BondData
from .fixed_rate_bond_data_entry import FixedRateBondDataEntry


class FixedRateBondData(BondData):
    def __init__(self, fixed_rate_bond_data_entries: list[FixedRateBondDataEntry]):
        super().__init__(fixed_rate_bond_data_entries)

    def to_master_data_frame(self) -> pd.DataFrame:
        df = self.to_data_frame()
        return df[["isin", "institute", "years_to_maturity", "max_interest_only_period", "coupon_rate"]]

    def to_spot_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        return df[["timestamp", "isin", "spot_price"]]

    def to_offer_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        return df[["timestamp", "isin", "offer_price"]]
