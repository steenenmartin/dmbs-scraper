import time as timeit
from datetime import datetime, time
from .bond_data.fixed_rate_bond_data import FixedRateBondData
from .database import sqlite_conn, postgres_conn
from .result_handlers.database_result_handler import DatabaseResultHandler
from .result_handlers.result_handler import ResultHandler
from .scrapers.scraper import Scraper
from .scrapers.scraper_orchestrator import ScraperOrchestrator
from .scrapers.jyske_scraper import JyskeScraper
from .scrapers.nordea_scraper import NordeaScraper
from .scrapers.total_kredit_scraper import TotalKreditScraper
from .scrapers.realkredit_danmark_scraper import RealKreditDanmarkScraper


def scrape():
    now = datetime.utcnow()
    now = datetime(now.year, now.month, now.day, now.hour, now.minute)

    prices_result_handler: ResultHandler = DatabaseResultHandler("prices", postgres_conn, now)
    if not prices_result_handler.result_exists():
        scrapers: list[Scraper] = [
            JyskeScraper(),
            RealKreditDanmarkScraper(),
            NordeaScraper(),
            TotalKreditScraper()
        ]

        fixed_rate_bond_data: FixedRateBondData = ScraperOrchestrator(scrapers).scrape()
        prices_result_handler.export_result(fixed_rate_bond_data.to_pandas_data_frame(now))

    if now.hour == 15 and now.minute == 5:
        ohlc_prices_result_handler = DatabaseResultHandler("ohlc_prices", postgres_conn, now)
        if not ohlc_prices_result_handler.result_exists():
            today = datetime(now.year, now.month, now.day)
            ohlc_prices = sqlite_conn.calculate_open_high_low_close_prices(today)
            ohlc_prices_result_handler.export_result(ohlc_prices)


if __name__ == "__main__":
    scrape()
