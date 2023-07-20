from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class JyskeScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        return [
            FixedRateBondDataEntry(
                self.institute.name,
                int(product["loebetidAar"]),
                float(product["aktuelKurs"]),
                float(product["tilbudsKurs"]),
                float(product["maxAntalAfdragsfrieAar"]),
                float(product["kuponrenteProcent"]),
                product["isin"]
            ) for product in data["fastRenteProdukter"]
        ]

    @Scraper.scraper
    def parse_floating_rate_bonds(self, data) -> list[FloatingRateBondDataEntry]:
        return [
            FloatingRateBondDataEntry(
                self.institute.name,
                int(product["fastrenteperiode"]),
                0,
                float(product["vaegtetTilbudskursProcent"]),
            ) for product in data["variabelRenteProdukter"]
        ]

    @property
    def url(self) -> str:
        return "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.Jyske

    @property
    def headers(self) -> dict:
        return {
            "Host": "jyskeberegner-api.jyskebank.dk",
            "Origin": "https://www.jyskebank.dk",
            "Referer": "https://www.jyskebank.dk/",
        }
