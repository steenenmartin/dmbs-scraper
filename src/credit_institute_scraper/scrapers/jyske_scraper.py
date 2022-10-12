from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
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

    @property
    def url(self) -> str:
        return "https://jyskeberegner-api.jyskebank.dk/api/privat/kursliste"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.Jyske

    @property
    def headers(self):
        return {
            "Accept": "application/json",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "da,en;q=0.9,de;q=0.8,sv;q=0.7",
            "Connection": "keep-alive",
            "Host": "jyskeberegner-api.jyskebank.dk",
            "Origin": "https://www.jyskebank.dk",
            "Referer": "https://www.jyskebank.dk/",
            "sec-ch-ua": '"Chromium";v="106", "Google Chrome";v="106", "Not;A=Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "Windows",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-site",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/106.0.0.0 Safari/537.36"
        }
