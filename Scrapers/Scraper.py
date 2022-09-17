import requests
import json

from FixedRateBond import FixedRateBond
from RealKreditInstitut import RealKreditInstitut


class Scraper:
    def __init__(self):
        self.scrape_success = False
        self.tries_count = 0

    @classmethod
    def scraper(cls, parse_bond_data_func):
        """
        This method is designed to be a decorator for the parse_fixed_rate_bonds-methods in child-Scraper classes.
        Sending the request and loading the .json data is done here in the super-class decorator, and then the child-specific data parsing is executed.

        :param parse_bond_data_func: The parsing function from child Scraper-class
        """
        def wrapper(self, *args, **kwargs):
            self.tries_count += 1

            data = json.loads(requests.get(self.url).text)

            bonds: list[FixedRateBond] = parse_bond_data_func(self, data)

            self.scrape_success = True
            return bonds

        return wrapper

    def parse_fixed_rate_bonds(self) -> list[FixedRateBond]:
        raise NotImplementedError

    @property
    def url(self) -> str:
        raise NotImplementedError

    @property
    def institute(self) -> RealKreditInstitut:
        raise NotImplementedError

    @property
    def max_tries(self):
        return 3

