import logging
import time
import pandas as pd
import pytz
from datetime import datetime

from ..enums.status import Status
from ..enums.credit_insitute import CreditInstitute
from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..result_handlers.database_result_handler import DatabaseResultHandler
from ..scrapers.scraper import Scraper
from ..scrapers.scraper_orchestrator import ScraperOrchestrator
from ..scrapers.jyske_scraper import JyskeScraper
from ..scrapers.nordea_scraper import NordeaScraper
from ..scrapers.total_kredit_scraper import TotalKreditScraper
from ..scrapers.realkredit_danmark_scraper import RealKreditDanmarkScraper
from ..scrapers.dlr_kredit_scraper import DlrKreditScraper
from ..database import load_data
from ..utils.date_helper import is_holiday


def scrape(conn_module, debug=False):
    try:
        # Get times (UTC and local CPH tz)
        utc_now = pytz.utc.localize(datetime.utcnow().replace(second=0, microsecond=0))
        now = utc_now.astimezone(pytz.timezone("Europe/Copenhagen"))
        today = datetime(now.year, now.month, now.day)
        utc_now = utc_now.replace(tzinfo=None)

        logging.info(f"Scraping at {now.tzname()} time {now.strftime('%Y-%m-%d %H:%M')} - {utc_now.tzname()} time {utc_now.strftime('%Y-%m-%d %H:%M')}")

        # Delay first scrape due to lagged update from credit institutes (120s not even enough..)
        if now.hour == 9 and now.minute == 0:
            time.sleep(120)

        # Only scrape in exchange opening hours (9-17 CPH time)
        if not debug:
            if now.hour < 9 or (now.hour >= 17 and now.minute > 0) or now.hour >= 18:
                return

            if is_holiday(today):
                return

        scrapers: list[Scraper] = [
            JyskeScraper(),
            RealKreditDanmarkScraper(),
            NordeaScraper(),
            TotalKreditScraper(),
            # DlrKreditScraper()
        ]

        # Scrape and upload spot prices
        fixed_rate_bond_data: FixedRateBondData = ScraperOrchestrator(scrapers).scrape()
        fixed_rate_bond_data_df = fixed_rate_bond_data.to_spot_prices_data_frame(utc_now).drop_duplicates()
        DatabaseResultHandler(conn_module, "spot_prices", utc_now).export_result(fixed_rate_bond_data_df)

        # Update master data for each scrape, adding new bonds if not in database.
        master_data_db = conn_module.query_db("select * from master_data")
        master_data = pd.concat([master_data_db, fixed_rate_bond_data.to_master_data_frame()]).drop_duplicates()
        DatabaseResultHandler(conn_module, "master_data", utc_now).export_result(master_data, if_exists="replace")

        # Update today's offer prices at exchange open
        if now.hour == 9 and now.minute == 0:
            offer_prices_result_handler = DatabaseResultHandler(conn_module, "offer_prices", utc_now)
            offer_prices_result_handler.export_result(fixed_rate_bond_data.to_offer_prices_data_frame(today))

        # Calculate and update OHLC prices table at exchange close.
        if now.hour == 17 and now.minute == 0:
            ohlc_prices_result_handler = DatabaseResultHandler(conn_module, "ohlc_prices", utc_now)
            ohlc_prices = load_data.calculate_open_high_low_close_prices(today, conn_module.query_db)
            ohlc_prices_result_handler.export_result(ohlc_prices)

        # Update today's closing prices with latest scraped data. Replace if exists to ensure one row per day.
        DatabaseResultHandler(conn_module, "closing_prices", today).export_result(fixed_rate_bond_data_df, if_exists="append")

        # Update status table
        update_status_table(conn_module, fixed_rate_bond_data, now, scrapers, utc_now)
    except Exception as e:
        DatabaseResultHandler(conn_module, "scrape_logs", datetime.utcnow()).export_result(pd.DataFrame(columns=["time", "error"], data=[[datetime.utcnow(), e]]))


def update_status_table(conn_module, fixed_rate_bond_data, now, scrapers, utc_now):
    current_status = conn_module.query_db("select * from status")
    status_columns = list(conn_module.query_db("select * from status").columns.values)
    status_data_frame = pd.DataFrame(columns=status_columns)
    current_status.set_index("institute", inplace=True)
    for institute in CreditInstitute:
        if any(scraper.missing_observations for scraper in scrapers if scraper.institute == institute):
            status = Status.SomeDataMissing
        elif len([bond for bond in fixed_rate_bond_data.fixed_rate_bond_data_entries if bond.institute == institute.name]) > 0:
            if current_status.loc[institute.name]["status"] in ([Status.NotOK.name, Status.SomeDataMissing.name]):
                status = Status.SomeDataMissing
            else:
                status = Status.OK
        else:
            status = Status.NotOK

        if now.hour == 17:
            status = Status.ExchangeClosed

        institute_status = pd.DataFrame(columns=status_columns)
        institute_status.loc[0] = [institute.name, utc_now, status.name]
        status_data_frame = pd.concat([status_data_frame, institute_status])
    DatabaseResultHandler(conn_module, "status", utc_now).export_result(status_data_frame, if_exists="replace")


