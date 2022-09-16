import os
import pandas as pd
from datetime import datetime

from FixedRateBond import FixedRateBond
from util import print_time_prefixed


class ScraperOrchestrator:
    def __init__(self, scrapers):
        self._scrapers = scrapers

    def try_scrape(self, scrape_time: datetime) -> bool:
        day_path = f"./Kurser/{scrape_time.strftime('%Y%m%d')}"
        if not os.path.exists(day_path):
            os.makedirs(day_path)

        csv_path = f"{day_path}/{scrape_time.strftime('%Y%m%d%H%M')}.csv"
        if not os.path.exists(csv_path):
            fixed_rate_bonds: list[FixedRateBond] = []

            # TODO: Allow for some scrapers to fail without returning false.
            #       Add results to already successful results on retry.
            #       Easier in database implementation (as opposed to csv).
            for scraper in self.scrapers:
                try:
                    fixed_rate_bonds.extend(scraper.parse_fixed_rate_bonds(scrape_time))
                    print_time_prefixed(f"Scraping '{scraper.institute.name}' succeeded")
                except Exception as e:
                    print_time_prefixed(f"Scraping '{scraper.institute.name}' failed: {e}")
                    return False

            pd.DataFrame.from_dict([x.__dict__ for x in fixed_rate_bonds]).to_csv(csv_path, index=False)
            return True

    @property
    def scrapers(self):
        return self._scrapers
