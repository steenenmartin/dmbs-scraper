from .bond_data_entry import BondDataEntry


class FloatingRateBondDataEntry(BondDataEntry):
    def __init__(self, institute: str, fixed_rate_period: int, max_interest_only_period: int, spot_rate: float):
        self.institute = institute
        self.fixed_rate_period = fixed_rate_period
        self.max_interest_only_period = max_interest_only_period
        self.spot_rate = spot_rate

