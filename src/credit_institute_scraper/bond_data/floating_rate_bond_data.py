import pandas as pd
import datetime as dt
from .floating_rate_bond_data_entry import FloatingRateBondDataEntry


class FloatingRateBondData:
    def __init__(self, floating_rate_bond_data_entries: list[FloatingRateBondDataEntry]):
        self.floating_rate_bond_data_entries = floating_rate_bond_data_entries

    def to_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = pd.DataFrame(x.__dict__ for x in self.floating_rate_bond_data_entries)
        if scrape_time is not None:
            df.insert(0, "timestamp", scrape_time)

        return df
