import pandas as pd
import datetime as dt
from .bond_data_entry import BondDataEntry


class BondData:
    def __init__(self, entries: list[BondDataEntry]):
        self.entries = entries

    def to_data_frame(self, scrape_time: dt.datetime = None) -> pd.DataFrame:
        df = pd.DataFrame(x.__dict__ for x in self.entries)
        if scrape_time is not None:
            df.insert(0, "timestamp", scrape_time)

        return df
