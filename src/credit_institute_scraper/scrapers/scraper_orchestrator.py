from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data import FloatingRateBondData
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..scrapers.scraper import Scraper
import logging


class ScraperOrchestrator:
    def __init__(self, scrapers: list[Scraper]):
        self._scrapers = scrapers

    def scrape_fixed_rate_bonds(self) -> FixedRateBondData:
        fixed_rate_bond_data_entries: list[FixedRateBondDataEntry] = []

        while not all(s.scrape_success or s.tries_count == s.max_tries for s in self.scrapers):
            for scraper in self.scrapers:
                if not scraper.scrape_success and scraper.tries_count < scraper.max_tries:
                    try:
                        fixed_rate_bond_data_entries.extend(scraper.parse_fixed_rate_bonds())
                        logging.info(f"Scraping '{scraper.institute.name}' succeeded")
                    except Exception as e:
                        logging.info(f"Scraping '{scraper.institute.name}' failed (try {scraper.tries_count}/{scraper.max_tries}): {e}")

        return FixedRateBondData(fixed_rate_bond_data_entries)

    def scrape_floating_rate_bonds(self) -> FloatingRateBondData:
        floating_rate_bond_data_entries: list[FloatingRateBondDataEntry] = []

        while not all(s.scrape_success or s.tries_count == s.max_tries for s in self.scrapers):
            for scraper in self.scrapers:
                if not scraper.scrape_success and scraper.tries_count < scraper.max_tries:
                    try:
                        floating_rate_bond_data_entries.extend(scraper.parse_floating_rate_bonds())
                        logging.info(f"Scraping '{scraper.institute.name}' succeeded")
                    except Exception as e:
                        logging.info(f"Scraping '{scraper.institute.name}' failed (try {scraper.tries_count}/{scraper.max_tries}): {e}")

        return FloatingRateBondData(floating_rate_bond_data_entries)

    @property
    def scrapers(self):
        return self._scrapers
