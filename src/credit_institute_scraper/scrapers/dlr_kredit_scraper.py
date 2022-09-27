from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class DlrKreditScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        x = 0
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(float(product["loebetid"])),
                float(product["kurs"]),
                float(product["afdragsfrihed"].split(" ")[0]) if product["afdragsfrihed"] != "" else 0.0,
                float(product["navn"].split(" ")[0].replace(",", ".").replace("%", "")),
                product["ISIN"]
            ) for product in data["obligationer"] if product["laanbeskrivelse"] == "Fastforrentede obligationslån"
        ]

    @property
    def url(self) -> str:
        return "https://dlr.dk/kurslisteservice?viseuro=N"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.DlrKredit
