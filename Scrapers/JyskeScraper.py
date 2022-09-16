from FixedRateBond import FixedRateBond
from RealKreditInstitut import RealKreditInstitut
from Scrapers.Scraper import Scraper


class JyskeScraper(Scraper):
    def __init__(self):
        pass

    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBond]:
        return [
            FixedRateBond(
                self.institute.name,
                int(product["loebetidAar"]),
                float(product["aktuelKurs"]),
                float(product["maxAntalAfdragsfrieAar"]),
                float(product["kuponrenteProcent"]),
                product["isin"]
            ) for product in data["fastRenteProdukter"]
        ]

    @property
    def url(self) -> str:
        return "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"

    @property
    def institute(self) -> RealKreditInstitut:
        return RealKreditInstitut.Jyske
