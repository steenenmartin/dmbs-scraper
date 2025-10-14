import requests
from requests.adapters import HTTPAdapter
import json
import urllib3
import ssl

from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute


def get_legacy_session():
    ctx = ssl.create_default_context(ssl.Purpose.SERVER_AUTH)
    ctx.options |= 0x4  # OP_LEGACY_SERVER_CONNECT
    session = requests.session()
    session.mount('https://', CustomHttpAdapter(ctx))
    return session


class Scraper:
    def __init__(self):
        self.scrape_success = False
        self.tries_count = 0
        self.missing_observations = False

    @classmethod
    def scraper(cls, parse_bond_data_func):
        """
        This method is designed to be a decorator for the parsing methods in Scraper child classes.
        Sending the request and loading the .json data is done here in the super-class decorator, and then the child-specific data parsing is executed.

        :param parse_bond_data_func: The parsing function from child Scraper-class
        """
        def wrapper(self):
            self.tries_count += 1

            data = self.get_data()

            bonds = parse_bond_data_func(self, data)

            self.scrape_success = True
            return bonds

        return wrapper

    def parse_fixed_rate_bonds(self) -> list[FixedRateBondDataEntry]:
        raise NotImplementedError

    def parse_floating_rate_bonds(self) -> list[FloatingRateBondDataEntry]:
        raise NotImplementedError

    @property
    def url(self) -> str:
        raise NotImplementedError

    @property
    def institute(self) -> CreditInstitute:
        raise NotImplementedError

    @property
    def max_tries(self) -> int:
        # Can be overridden by each Scraper-child class if necessary.
        return 3

    @property
    def headers(self) -> dict:
        # Can be overridden by each Scraper-child class if necessary. See eg. jyske_scraper
        return {}

    def get_data(self):
        return json.loads(get_legacy_session().get(self.url, headers=self.headers, timeout=10).text)


class CustomHttpAdapter(HTTPAdapter):
    # "Transport adapter" that allows us to use custom ssl_context.

    def __init__(self, ssl_context=None, **kwargs):
        self.ssl_context = ssl_context
        super().__init__(**kwargs)

    def init_poolmanager(self, connections, maxsize, block=False):
        self.poolmanager = urllib3.poolmanager.PoolManager(
            num_pools=connections, maxsize=maxsize,
            block=block, ssl_context=self.ssl_context)

