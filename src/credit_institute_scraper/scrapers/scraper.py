import logging
import math
from functools import wraps

import requests

from ..bond_data.validation import validate_bond
from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry


class EmptyScrapeError(ValueError):
    """No usable products were returned; the orchestrator may retry."""


class Scraper:
    def __init__(self):
        self.reset()

    def reset(self):
        self.scrape_success = False
        self.tries_count = 0
        self.missing_observations = False
        self.issues = []
        self._data_cache = None

    def report_issue(self, message):
        self.missing_observations = True
        self.issues.append(message)
        logging.warning('%s: %s', self.institute.name, message)

    def parse_products(self, products, parse_product):
        if not isinstance(products, list):
            raise ValueError('Expected a product list')
        bonds = []
        for index, product in enumerate(products):
            try:
                bond = parse_product(product)
                if bond is not None:
                    bonds.append(bond)
            except (KeyError, ValueError, TypeError, IndexError, AttributeError, NotImplementedError) as error:
                # Do not log full provider responses or let one bad product hide all others.
                self.report_issue(f'Product {index} rejected during parsing: {type(error).__name__}: {error}')
        return bonds

    @staticmethod
    def scraper(parse_bond_data_func):
        @wraps(parse_bond_data_func)
        def wrapper(self):
            self.tries_count += 1
            self.scrape_success = False
            bonds = parse_bond_data_func(self, self.get_data())
            valid_bonds = []
            for bond in bonds:
                try:
                    valid_bonds.append(validate_bond(bond, self.institute.name))
                    if isinstance(bond, FixedRateBondDataEntry) and not math.isfinite(bond.spot_price):
                        self.report_issue(f'Observation {bond.isin} has no usable spot price; retaining master data only')
                except (ValueError, TypeError, OverflowError) as error:
                    product = getattr(bond, 'isin', None) or f'F{getattr(bond, "fixed_rate_period", "?")}/IO{getattr(bond, "max_interest_only_period", "?")}'
                    self.report_issue(f'Observation {product} rejected: {error}')
            if not valid_bonds:
                raise EmptyScrapeError('No valid observations')
            self.scrape_success = True
            return valid_bonds
        return wrapper

    @property
    def max_tries(self):
        return 3

    @property
    def headers(self):
        return {}

    def get_data(self):
        # Always verify TLS and HTTP status; HTML error pages are not feed data.
        with requests.Session() as session:
            with session.get(self.url, headers=self.headers, timeout=(5, 20)) as response:
                response.raise_for_status()
                return response.json()
