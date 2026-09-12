"""Shared validation for parsed observations; no guessed market values."""
import math
import re

from .fixed_rate_bond_data_entry import FixedRateBondDataEntry
from .floating_rate_bond_data_entry import FloatingRateBondDataEntry


def number(value, field, *, integer=False):
    if isinstance(value, bool):
        raise ValueError(f'{field} must be numeric')
    value = float(value)
    if not math.isfinite(value) or (integer and (value < 0 or not value.is_integer())):
        raise ValueError(f'Invalid {field}')
    return int(value) if integer else value


def validate_bond(bond, institute):
    if bond.institute != institute:
        raise ValueError('Unexpected institute')
    bond.max_interest_only_period = number(bond.max_interest_only_period, 'interest-only period', integer=True)
    if isinstance(bond, FloatingRateBondDataEntry):
        bond.fixed_rate_period = number(bond.fixed_rate_period, 'fixed rate period', integer=True)
        bond.spot_rate = number(bond.spot_rate, 'spot rate')
        if bond.fixed_rate_period == 0 or bond.spot_rate == 0:
            raise ValueError('Missing floating rate or fixed rate period')
    elif isinstance(bond, FixedRateBondDataEntry):
        if not isinstance(bond.isin, str) or not re.fullmatch(r'[A-Z]{2}[A-Z0-9]{9}[0-9]', bond.isin):
            raise ValueError('Invalid ISIN')
        bond.years_to_maturity = number(bond.years_to_maturity, 'loan term', integer=True)
        bond.coupon_rate = number(bond.coupon_rate, 'coupon rate')
        if bond.years_to_maturity == 0 or bond.max_interest_only_period > bond.years_to_maturity:
            raise ValueError('Invalid loan term / interest-only period')
        # Absent prices must not discard otherwise useful master data.
        for field in ('spot_price', 'offer_price'):
            value = getattr(bond, field)
            value = float(value) if value is not None else float('nan')
            if not math.isfinite(value) or value <= 0:
                value = float('nan')
            setattr(bond, field, value)
    else:
        raise ValueError('Unexpected observation type')
    return bond
