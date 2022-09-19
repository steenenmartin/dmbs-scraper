from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..types.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class TotalKreditScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(float(product["lifetime"].split(" ")[0])),
                float(product["spotPriceRatePayment"].replace(",", ".")),
                0.0 if product["name"].endswith("med afdrag") else float(product["name"].split(" ")[5]),
                float(product["name"].split(" ")[0].strip("%").replace(",", ".")),
                "DKK000" + product["fondCode"]
            ) for product in data["groups"][0]['entries']
        ]

    @property
    def url(self) -> str:
        return "https://www.totalkredit.dk//api/bondinformation/table?tableId=privat-udbetaling-af-laan-aktuelle-kurser-kunder&domain=totalkredit"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.TotalKredit
