import pandas as pd
import datetime as dt
from .fixed_rate_bond_data_entry import FixedRateBondDataEntry


class FixedRateBondData:
    def __init__(self, fixed_rate_bond_data_entries: list[FixedRateBondDataEntry]):
        self.fixed_rate_bond_data_entries = fixed_rate_bond_data_entries

    def to_spot_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        df = df.drop("offer_price", axis=1)

        return df

    def to_offer_prices_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = self.to_data_frame(scrape_time)
        df = df.drop("spot_price", axis=1)

        return df

    def to_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = pd.DataFrame(x.__dict__ for x in self.fixed_rate_bond_data_entries)
        if scrape_time is not None:
            df.insert(0, "timestamp", scrape_time)

        return df
