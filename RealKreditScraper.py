import time as timeit
from datetime import datetime, time
from Plotting import create_single_day_plot_per_institute, create_multi_day_plot
from ResultHandlers.CsvResultHandler import CsvResultHandler
from ResultHandlers.ResultHandler import ResultHandler
from Scrapers.Scraper import Scraper
from util import print_time_prefixed

from Scrapers.ScraperOrchestrator import ScraperOrchestrator
from Scrapers.JyskeScraper import JyskeScraper
from Scrapers.NordeaScraper import NordeaScraper
from Scrapers.TotalKreditScraper import TotalKreditScraper
from Scrapers.RealKreditDanmarkScraper import RealKreditDanmarkScraper


if __name__ == "__main__":
    # TODO: Remove while-loop when program is executed using pinger/task-scheduler.
    while True:
        start_time = timeit.time()
        now = datetime.utcnow()

        scrapers: list[Scraper] = [
            JyskeScraper(),
            RealKreditDanmarkScraper(),
            NordeaScraper(),
            TotalKreditScraper()
        ]

        result_handler: ResultHandler = CsvResultHandler(now)

        scraper_orchestrator = ScraperOrchestrator(scrapers)

        if now.minute % 5 == 0:
            # TODO: Incorporate accounting for Danish banking holidays.
            if time(7, 0) <= now.time() < time(15, 1) and now.isoweekday() <= 5:
                if not result_handler.result_exists():
                    fixed_rate_bonds = scraper_orchestrator.scrape()
                    result_handler.export_result(fixed_rate_bonds)
                    create_single_day_plot_per_institute(now.today())

            if now.hour == 15 and now.minute == 5:
                # create_multi_day_plot()
                # print_time_prefixed("Updated multi day plot")
                timeit.sleep(60)

        timeit.sleep(max(10 - (timeit.time() - start_time), 0))
