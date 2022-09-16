import requests
import json

from FixedRateBond import FixedRateBond
from RealKreditInstitut import RealKreditInstitut


class Scraper:
    @classmethod
    def scraper(cls, parse_bonds):
        def wrapper(self, *args, **kwargs):
            data = json.loads(requests.get(self.url).text)
            return parse_bonds(self, data)

        return wrapper

    def parse_fixed_rate_bonds(self) -> list[FixedRateBond]:
        raise NotImplementedError

    @property
    def url(self) -> str:
        raise NotImplementedError

    @property
    def institute(self) -> RealKreditInstitut:
        raise NotImplementedError
