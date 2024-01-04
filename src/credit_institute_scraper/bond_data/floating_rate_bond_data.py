import pandas as pd

from .bond_data import BondData
from .floating_rate_bond_data_entry import FloatingRateBondDataEntry


class FloatingRateBondData(BondData):
    def __init__(self, floating_rate_bond_data_entries: list[FloatingRateBondDataEntry]):
        super().__init__(floating_rate_bond_data_entries)

    def to_master_data_frame(self) -> pd.DataFrame:
        df = self.to_data_frame()
        return df[["institute", "fixed_rate_period", "max_interest_only_period"]]
