from datetime import datetime
from credit_institute_scraper.bond_data.fixed_rate_bond_data import FixedRateBondData
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler
from credit_institute_scraper.result_handlers.result_handler import ResultHandler
from credit_institute_scraper.scrapers.scraper import Scraper
from credit_institute_scraper.scrapers.scraper_orchestrator import ScraperOrchestrator
from credit_institute_scraper.scrapers.jyske_scraper import JyskeScraper
from credit_institute_scraper.scrapers.nordea_scraper import NordeaScraper
from credit_institute_scraper.scrapers.total_kredit_scraper import TotalKreditScraper
from credit_institute_scraper.scrapers.realkredit_danmark_scraper import RealKreditDanmarkScraper
from credit_institute_scraper.database import load_data


def scrape(conn_module):
    now = datetime.utcnow()
    now = datetime(now.year, now.month, now.day, now.hour, now.minute)

    prices_result_handler: ResultHandler = DatabaseResultHandler(conn_module, "prices", now)
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
        ohlc_prices_result_handler = DatabaseResultHandler(conn_module, "ohlc_prices", now)
        if not ohlc_prices_result_handler.result_exists():
            today = datetime(now.year, now.month, now.day)
            ohlc_prices = load_data.calculate_open_high_low_close_prices(today, conn_module.query_db)
            ohlc_prices_result_handler.export_result(ohlc_prices)

