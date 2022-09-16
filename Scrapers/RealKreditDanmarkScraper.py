from FixedRateBond import FixedRateBond
from RealKreditInstitut import RealKreditInstitut
from Scrapers.Scraper import Scraper


class RealKreditDanmarkScraper(Scraper):
    def __init__(self):
        pass

    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBond]:
        return [
            FixedRateBond(
                self.institute.name,
                int(float(product["termToMaturityYears"])),
                float(product["prices"][0]["price"].replace(",", ".")),
                float(product["numberOfTermsWithoutRepayment"]) * 3 / 12,
                float(product["nominelInterestRate"]),
                product["isinCode"]
            ) for product in data
        ]

    @property
    def url(self) -> str:
        return "https://rd.dk/api/Rates/GetOpenOffers"

    @property
    def institute(self) -> RealKreditInstitut:
        return RealKreditInstitut.RealKreditDanmark
