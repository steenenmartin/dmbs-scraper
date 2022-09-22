import time as timeit
from datetime import datetime, time

from credit_institute_scraper.bond_data.fixed_rate_bond_data import FixedRateBondData
from credit_institute_scraper.database import sqlite_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler
from credit_institute_scraper.result_handlers.result_handler import ResultHandler
from credit_institute_scraper.scrapers.scraper import Scraper
from credit_institute_scraper.scrapers.scraper_orchestrator import ScraperOrchestrator
from credit_institute_scraper.scrapers.jyske_scraper import JyskeScraper
from credit_institute_scraper.scrapers.nordea_scraper import NordeaScraper
from credit_institute_scraper.scrapers.total_kredit_scraper import TotalKreditScraper
from credit_institute_scraper.scrapers.realkredit_danmark_scraper import RealKreditDanmarkScraper


def main():
    # TODO: Remove while-loop when program is executed using pinger/task-scheduler.
    while True:
        start_time = timeit.time()
        now = datetime.utcnow()
        now = datetime(now.year, now.month, now.day, now.hour, now.minute)

        # TODO: Incorporate accounting for Danish banking holidays.
        if now.isoweekday() <= 5:
            if time(7, 0) <= now.time() < time(15, 1) and now.minute % 5 == 0:
                prices_result_handler: ResultHandler = DatabaseResultHandler("prices", now)
                if not prices_result_handler.result_exists():
                    scrapers: list[Scraper] = [
                        JyskeScraper(),
                        RealKreditDanmarkScraper(),
                        NordeaScraper(),
                        TotalKreditScraper()
                    ]

                    fixed_rate_bond_data: FixedRateBondData = ScraperOrchestrator(scrapers).scrape()
                    prices_result_handler.export_result(fixed_rate_bond_data.to_pandas_data_frame(now))
                    # create_single_day_plot_per_institute(now.today())

            if now.hour == 15 and now.minute == 1:
                ohlc_prices_result_handler = DatabaseResultHandler("ohlc_prices", now)
                if not ohlc_prices_result_handler.result_exists():
                    today = datetime(now.year, now.month, now.day)
                    ohlc_prices = sqlite_conn.calculate_open_high_low_close_prices(today)
                    ohlc_prices_result_handler.export_result(ohlc_prices)

                # create_multi_day_plot()
                # print_time_prefixed("Updated multi day plot")
                # timeit.sleep(60)

        timeit.sleep(max(10 - (timeit.time() - start_time), 0))


if __name__ == "__main__":
    main()
