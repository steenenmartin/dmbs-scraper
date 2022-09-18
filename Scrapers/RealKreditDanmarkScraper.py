from BondData.FixedRateBondDataEntry import FixedRateBondDataEntry
from RealKreditInstitut import RealKreditInstitut
from Scrapers.Scraper import Scraper


class RealKreditDanmarkScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(float(product["termToMaturityYears"])),
                float(product["prices"][0]["price"].replace(",", ".")),
                float(product["numberOfTermsWithoutRepayment"]) * 3.0 / 12.0,
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
