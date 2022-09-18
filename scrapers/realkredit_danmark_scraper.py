from bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from credit_insitute import CreditInstitute
from scrapers.scraper import Scraper


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
    def institute(self) -> CreditInstitute:
        return CreditInstitute.RealKreditDanmark
