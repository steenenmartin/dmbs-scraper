import re

from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class TotalKreditFloatingScraper(Scraper):
    @Scraper.scraper
    def parse_floating_rate_bonds(self, data) -> list[FloatingRateBondDataEntry]:
        bonds: list[FloatingRateBondDataEntry] = []
        for product in data["groups"][0]['entries']:
            if product["name"].endswith("med afdrag"):
                max_io_period = 0
            elif product["name"].endswith("års afdragsfrihed"):
                regex_result = re.search("(F\\d{1,2} med op til )(\\d{2})( års afdragsfrihed)", product["name"])
                max_io_period = regex_result.group(2)
            else:
                raise NotImplementedError()

            bond = FloatingRateBondDataEntry(
                self.institute.name,
                int(product["name"].split(" ")[0].replace("F", "")),
                max_io_period,
                float(product["innerInterestGrossValue"].replace("%", "").replace(",", "."))
            )

            bonds.append(bond)

        return bonds

    @property
    def url(self) -> str:
        return "https://www.totalkredit.dk//api/bondinformation/table?tableId=privat-udbetaling-af-laan-kontantrenter-raadgivere-og-kunder&domain=totalkredit"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.TotalKredit
