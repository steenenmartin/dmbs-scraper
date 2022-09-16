import time as timeit
from datetime import datetime, time
from Plotting import create_single_day_plot, create_multi_day_plot
from Scrapers.Scraper import Scraper
from util import print_time_prefixed

from Scrapers.ScraperOrchestrator import ScraperOrchestrator
from Scrapers.JyskeScraper import JyskeScraper
from Scrapers.NordeaScraper import NordeaScraper
from Scrapers.TotalKreditScraper import TotalKreditScraper
from Scrapers.RealKreditDanmarkScraper import RealKreditDanmarkScraper


if __name__ == "__main__":
    while True:
        start_time = timeit.time()
        now = datetime.utcnow()

        scrapers: list[Scraper] = [
            JyskeScraper(),
            RealKreditDanmarkScraper(),
            NordeaScraper(),
            TotalKreditScraper()
        ]

        scraper_orchestrator = ScraperOrchestrator(scrapers)

        scraper_orchestrator.try_scrape(now)
        if now.minute % 5 == 0:
            if time(7, 0) <= now.time() < time(15, 1) and now.isoweekday() <= 5:
                if scraper_orchestrator.try_scrape(now):
                    pass
                    # create_single_day_plot(now.today())

            if now.hour == 15 and now.minute == 5:
                # create_multi_day_plot()
                # print_time_prefixed("Updated multi day plot")
                timeit.sleep(60)

        timeit.sleep(max(10 - (timeit.time() - start_time), 0))
