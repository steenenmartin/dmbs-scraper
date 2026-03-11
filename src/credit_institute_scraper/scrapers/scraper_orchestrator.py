from concurrent.futures import ThreadPoolExecutor, as_completed

from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from ..bond_data.floating_rate_bond_data import FloatingRateBondData
from ..bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from ..scrapers.scraper import Scraper
import logging


class ScraperOrchestrator:
    def __init__(self, scrapers: list[Scraper]):
        self._scrapers = scrapers

    def _scrape_single(self, scraper, parse_method_name):
        """Run a single scraper's parse method, returning (scraper, entries) or (scraper, error)."""
        try:
            entries = getattr(scraper, parse_method_name)()
            logging.info(f"Scraping '{scraper.institute.name}' succeeded")
            return scraper, entries, None
        except Exception as e:
            logging.info(f"Scraping '{scraper.institute.name}' failed (try {scraper.tries_count}/{scraper.max_tries}): {e}")
            return scraper, [], e

    def _scrape_all(self, parse_method_name):
        """Run all scrapers concurrently with retry logic, returning collected entries."""
        all_entries = []

        while not all(s.scrape_success or s.tries_count == s.max_tries for s in self.scrapers):
            pending = [s for s in self.scrapers if not s.scrape_success and s.tries_count < s.max_tries]
            if not pending:
                break

            with ThreadPoolExecutor(max_workers=len(pending)) as executor:
                futures = {
                    executor.submit(self._scrape_single, scraper, parse_method_name): scraper
                    for scraper in pending
                }
                for future in as_completed(futures):
                    scraper, entries, error = future.result()
                    if not error:
                        all_entries.extend(entries)

        return all_entries

    def scrape_fixed_rate_bonds(self) -> FixedRateBondData:
        return FixedRateBondData(self._scrape_all("parse_fixed_rate_bonds"))

    def scrape_floating_rate_bonds(self) -> FloatingRateBondData:
        return FloatingRateBondData(self._scrape_all("parse_floating_rate_bonds"))

    @property
    def scrapers(self):
        return self._scrapers
