from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..scrapers.scraper import Scraper
import logging


class ScraperOrchestrator:
    def __init__(self, scrapers: list[Scraper]):
        self._scrapers = scrapers

    def scrape(self) -> FixedRateBondData:
        fixed_rate_bond_data_entries: list[FixedRateBondDataEntry] = []
        while True:
            for scraper in self.scrapers:
                if not scraper.scrape_success and scraper.tries_count < scraper.max_tries:
                    try:
                        fixed_rate_bond_data_entries.extend(scraper.parse_fixed_rate_bonds())
                        logging.info(f"Scraping '{scraper.institute.name}' succeeded")
                    except Exception as e:
                        logging.info(f"Scraping '{scraper.institute.name}' failed (try {scraper.tries_count}/{scraper.max_tries}): {e}")

            if all(s.scrape_success or s.tries_count == s.max_tries for s in self.scrapers):
                break

        return FixedRateBondData(fixed_rate_bond_data_entries)

    @property
    def scrapers(self):
        return self._scrapers
