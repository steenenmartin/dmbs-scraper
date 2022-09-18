from BondData.FixedRateBondDataEntry import FixedRateBondDataEntry
from RealKreditInstitut import RealKreditInstitut
from Scrapers.Scraper import Scraper


class NordeaScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(product["loanPeriodMax"]),
                float(product["rate"].strip("*&nbsp;").replace(",", ".")),
                float(product["repaymentFreedomMax"]) if product["repaymentFreedomMax"] != "Nej" else 0,
                float(product["fundName"].split(" ")[0].strip("%").replace(",", ".")),
                product["isinCode"]
            ) for product in data
        ]

    @property
    def url(self) -> str:
        return "https://ebolig.nordea.dk/wemapp/api/credit/fixedrate/bonds.json"

    @property
    def institute(self) -> RealKreditInstitut:
        return RealKreditInstitut.Nordea
