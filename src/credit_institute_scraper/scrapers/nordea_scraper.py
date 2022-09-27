from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class NordeaScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(product["loanPeriodMax"]),
                float(product["rate"].replace(",", ".")) if not product["rate"].startswith("*&nbsp;") else float('nan'),
                float('nan'),
                float(product["repaymentFreedomMax"]) if product["repaymentFreedomMax"] != "Nej" else 0.0,
                float(product["fundName"].split(" ")[0].strip("%").replace(",", ".")),
                product["isinCode"]
            ) for product in data
        ]

    @property
    def url(self) -> str:
        return "https://ebolig.nordea.dk/wemapp/api/credit/fixedrate/bonds.json"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.Nordea
