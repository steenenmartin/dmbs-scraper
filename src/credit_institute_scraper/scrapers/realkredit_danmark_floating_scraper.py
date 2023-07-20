import re

from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class RealKreditDanmarkFloatingScraper(Scraper):
    @Scraper.scraper
    def parse_floating_rate_bonds(self, data) -> list[FloatingRateBondDataEntry]:
        bonds: list[FloatingRateBondDataEntry] = []
        for product in data:
            if re.match("^FlexLoan_F\\d{1,2}_", product["name"]):
                bond = FloatingRateBondDataEntry(
                    self.institute.name,
                    int(product["name"].replace("FlexLoan_F", "").replace("_WithInstallment", "").replace("_WithoutInstallment", "")),
                    0 if product["name"].endswith("WithInstallment") else 30,
                    float(product["offerrate"])
                )

                bonds.append(bond)

        return bonds

    @property
    def url(self) -> str:
        return "https://rd.dk/api/Rates/GetVariableLoans"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.RealKreditDanmark
