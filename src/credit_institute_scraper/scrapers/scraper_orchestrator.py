import logging
import time

from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..bond_data.floating_rate_bond_data import FloatingRateBondData


class ScraperOrchestrator:
    def __init__(self, scrapers, *, sleep=time.sleep):
        self._scrapers = scrapers
        self._sleep = sleep

    def _scrape(self, method, collection):
        entries = []
        for scraper in self.scrapers:
            scraper.reset()
            # Bounded independently of decorator counters: even a broken adapter
            # cannot create the old infinite retry loop.
            for attempt in range(1, scraper.max_tries + 1):
                try:
                    observations = getattr(scraper, method)()
                    if not observations:
                        raise ValueError('No valid observations')
                    entries.extend(observations)
                    scraper.scrape_success = True
                    logging.info('Scraped %s: %d observations, %d issues', scraper.institute.name, len(observations), len(scraper.issues))
                    break
                except Exception as error:
                    scraper.scrape_success = False
                    scraper._data_cache = None
                    scraper.report_issue(f'{method} attempt {attempt}/{scraper.max_tries} failed: {type(error).__name__}: {error}')
                    if attempt < scraper.max_tries:
                        self._sleep(min(2 ** (attempt - 1), 8))
            if not scraper.scrape_success:
                logging.error('Scraping exhausted for %s (%s)', scraper.institute.name, method)
        return collection(entries)

    def scrape_fixed_rate_bonds(self):
        return self._scrape('parse_fixed_rate_bonds', FixedRateBondData)

    def scrape_floating_rate_bonds(self):
        return self._scrape('parse_floating_rate_bonds', FloatingRateBondData)

    @property
    def scrapers(self):
        return self._scrapers
