from RealKreditInstitut import RealKreditInstitut


# TODO: Implement as dataclass.
class FixedRateBond:
    def __init__(self, institute: RealKreditInstitut, years_to_maturity: int, spot_price: float, maximum_years_without_repayment: float, coupon_rate: float, isin: str):
        self.institute = institute
        self.years_to_maturity = years_to_maturity
        self.spot_price = spot_price
        self.maximum_years_without_repayment = maximum_years_without_repayment
        self.coupon_rate = coupon_rate
        self.isin = isin