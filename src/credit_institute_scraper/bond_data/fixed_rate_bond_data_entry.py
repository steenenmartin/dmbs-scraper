class FixedRateBondDataEntry:
    def __init__(self,
                 institute: str,
                 years_to_maturity: int,
                 spot_price: float,
                 max_interest_only_period: float,
                 coupon_rate: float,
                 isin: str):
        self.institute = institute
        self.isin = isin
        self.years_to_maturity = years_to_maturity
        self.max_interest_only_period = max_interest_only_period
        self.coupon_rate = coupon_rate
        self.spot_price = spot_price
