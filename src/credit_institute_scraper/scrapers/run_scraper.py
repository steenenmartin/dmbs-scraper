from datetime import datetime

from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..result_handlers.database_result_handler import DatabaseResultHandler
from ..result_handlers.result_handler import ResultHandler
from ..scrapers.scraper import Scraper
from ..scrapers.scraper_orchestrator import ScraperOrchestrator
from ..scrapers.jyske_scraper import JyskeScraper
from ..scrapers.nordea_scraper import NordeaScraper
from ..scrapers.total_kredit_scraper import TotalKreditScraper
from ..scrapers.realkredit_danmark_scraper import RealKreditDanmarkScraper
from ..scrapers.dlr_kredit_scraper import DlrKreditScraper
from ..database import load_data


def scrape(conn_module):
    now = datetime.utcnow()
    now = datetime(now.year, now.month, now.day, now.hour, now.minute)

    prices_result_handler: ResultHandler = DatabaseResultHandler(conn_module, "prices", now)
    # if not prices_result_handler.result_exists():
    scrapers: list[Scraper] = [
        JyskeScraper(),
        RealKreditDanmarkScraper(),
        NordeaScraper(),
        TotalKreditScraper(),
        DlrKreditScraper()
    ]

    fixed_rate_bond_data: FixedRateBondData = ScraperOrchestrator(scrapers).scrape()
    prices_result_handler.export_result(fixed_rate_bond_data.to_spot_prices_data_frame(now))

    if now.hour == 7 and now.minute == 0:
        offer_prices_result_handler = DatabaseResultHandler(conn_module, "offer_prices", now)
        offer_prices_result_handler.export_result(fixed_rate_bond_data.to_offer_prices_data_frame(now))

    if now.hour == 15 and now.minute == 0:
        ohlc_prices_result_handler = DatabaseResultHandler(conn_module, "ohlc_prices", now)
        today = datetime(now.year, now.month, now.day)
        ohlc_prices = load_data.calculate_open_high_low_close_prices(today, conn_module.query_db)
        ohlc_prices_result_handler.export_result(ohlc_prices)

