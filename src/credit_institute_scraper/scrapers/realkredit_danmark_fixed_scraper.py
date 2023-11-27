from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..enums.credit_insitute import CreditInstitute
from ..scrapers.scraper import Scraper


class RealKreditDanmarkFixedScraper(Scraper):
    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data) -> list[FixedRateBondDataEntry]:
        bonds: list[FixedRateBondDataEntry] = []
        for product in data:
            years_to_maturity = int(float(product["termToMaturityYears"]))
            isin = product["isinCode"]

            loan_type_code = product["loanTypeCode"]

            if loan_type_code != "01":
                # wtf are these
                continue

            if isin == "DK0004618733" and years_to_maturity == 0:
                years_to_maturity = 30

            max_io_terms = float(product["numberOfTermsWithoutRepayment"])
            if max_io_terms == 119.0:
                max_io_terms = 120.0

            max_io_years = max_io_terms * 3.0 / 12.0

            price = float(product["prices"][0]["price"].replace(",", "."))
            if price <= 0.0:
                price = float('nan')
                self.missing_observations = True

            bond = FixedRateBondDataEntry(
                self.institute.name,
                years_to_maturity,
                price,
                float(product["offerprice"]),
                max_io_years,
                float(product["nominelInterestRate"]),
                isin
            )

            bonds.append(bond)

        return bonds

    @property
    def url(self) -> str:
        return "https://rd.dk/api/Rates/GetOpenOffers"

    @property
    def institute(self) -> CreditInstitute:
        return CreditInstitute.RealKreditDanmark
