from FixedRateBond import FixedRateBond
from Scrapers.Scraper import Scraper
from util import print_time_prefixed


class ScraperOrchestrator:
    def __init__(self, scrapers: list[Scraper]):
        self._scrapers = scrapers

    def scrape(self) -> list[FixedRateBond]:
        fixed_rate_bonds: list[FixedRateBond] = []
        while True:
            for scraper in self.scrapers:
                if not scraper.scrape_success and scraper.tries_count < scraper.max_tries:
                    try:
                        fixed_rate_bonds.extend(scraper.parse_fixed_rate_bonds())
                        print_time_prefixed(f"Scraping '{scraper.institute.name}' succeeded")
                    except Exception as e:
                        print_time_prefixed(f"Scraping '{scraper.institute.name}' failed: {e}")

            if all(s.scrape_success or s.tries_count == s.max_tries for s in self.scrapers):
                break

        return fixed_rate_bonds

    @property
    def scrapers(self):
        return self._scrapers
