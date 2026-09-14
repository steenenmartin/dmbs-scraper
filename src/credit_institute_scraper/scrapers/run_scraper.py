"""Fetch outside the transaction; commit one validated cycle atomically."""
import json
import logging
import threading
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pandas as pd

from .jyske_scraper import JyskeScraper
from .nordea_scraper import NordeaScraper
from .realkredit_danmark_fixed_scraper import RealKreditDanmarkFixedScraper
from .realkredit_danmark_floating_scraper import RealKreditDanmarkFloatingScraper
from .total_kredit_fixed_scraper import TotalKreditFixedScraper
from .total_kredit_floating_scraper import TotalKreditFloatingScraper
from .scraper_orchestrator import ScraperOrchestrator
from ..bond_data.floating_rate_bond_data import FloatingRateBondData
from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..database.ingestion import transaction, execute, write_observations, write_status, write_log
from ..database.master_data import insert_master_data
from ..database.load_data import calculate_open_high_low_close_prices
from ..enums.status import Status
from ..utils.date_helper import is_holiday


class CycleWarnings(logging.Handler):
    """Bounded audit summary, persisted even when a source only partially succeeds."""
    def __init__(self):
        super().__init__(logging.WARNING)
        self.thread = threading.get_ident()
        self.messages = []
        self.total = 0

    def emit(self, record):
        if record.thread == self.thread:
            self.total += 1
            if len(self.messages) < 100:
                self.messages.append(record.getMessage()[:2000])


def _daily_scrapers(conn_module, today, candidates):
    if not candidates:
        return [], {}
    rates = conn_module.query_db('SELECT institute, fixed_rate_period, max_interest_only_period FROM rates WHERE timestamp=:today', params={'today': today})
    master = conn_module.query_db('SELECT institute, fixed_rate_period, max_interest_only_period FROM master_data_float')
    def keys(frame, institute):
        return {(int(row.fixed_rate_period), int(row.max_interest_only_period))
                for row in frame.itertuples() if row.institute == institute}
    # Retry missing products later in the day, not just at exactly 09:00.
    missing = {scraper.institute.name: keys(master, scraper.institute.name) - keys(rates, scraper.institute.name)
               for scraper in candidates}
    return ([scraper for scraper in candidates if not keys(rates, scraper.institute.name)
             or missing[scraper.institute.name]], missing)


def scrape(conn_module, debug=False, *, now=None, fixed_scrapers=None, floating_scrapers=None):
    now = now or datetime.now(timezone.utc)
    if now.tzinfo is None:
        raise ValueError('Scrape time must include a timezone')
    local = now.astimezone(ZoneInfo('Europe/Copenhagen'))
    if not debug and (local.weekday() >= 5 or is_holiday(local) or local.hour < 9
                      or local.hour > 17 or (local.hour == 17 and local.minute >= 5)):
        return False
    # Stable five-minute keys make retries and overlapping workers idempotent.
    stamp = now.astimezone(timezone.utc)
    stamp = stamp.replace(tzinfo=None, minute=stamp.minute - stamp.minute % 5, second=0, microsecond=0)
    today = datetime(local.year, local.month, local.day)
    fixed_scrapers = fixed_scrapers if fixed_scrapers is not None else [JyskeScraper(), RealKreditDanmarkFixedScraper(), NordeaScraper(), TotalKreditFixedScraper()]
    floating_candidates = floating_scrapers if floating_scrapers is not None else [JyskeScraper(), RealKreditDanmarkFloatingScraper(), TotalKreditFloatingScraper()]
    audit = CycleWarnings()
    logging.getLogger().addHandler(audit)
    try:
        floating_scrapers, missing_products = _daily_scrapers(conn_module, today, floating_candidates)
        fixed = ScraperOrchestrator(fixed_scrapers).scrape_fixed_rate_bonds()
        floating = (ScraperOrchestrator(floating_scrapers).scrape_floating_rate_bonds()
                    if floating_scrapers else FloatingRateBondData([]))
        for source in floating_scrapers:
            observed = {(row.fixed_rate_period, row.max_interest_only_period) for row in floating.entries
                        if row.institute == source.institute.name}
            missing = missing_products[source.institute.name] - observed
            if missing:
                source.report_issue(f'Missing known floating products (fixed period, interest-only period): {sorted(missing)}')
        with transaction(conn_module) as connection:
            # Missing migration fails before prices are written. Every write in
            # this cycle rolls back if any later write fails.
            insert_master_data(connection, fixed.to_master_data_frame(), 'master_data')
            insert_master_data(connection, floating.to_master_data_frame(), 'master_data_float')
            identities = set(execute(connection, 'SELECT isin, institute, coupon_rate FROM master_data').fetchall())
            accepted = [bond for bond in fixed.entries if (bond.isin, bond.institute, bond.coupon_rate) in identities]
            if len(accepted) != len(fixed.entries):
                logging.warning('Rejected prices for %d observations without matching master identity', len(fixed.entries) - len(accepted))
            fixed = FixedRateBondData(accepted)
            write_observations(connection, fixed.to_spot_prices_data_frame(stamp), 'spot_prices')
            write_observations(connection, floating.to_data_frame(today), 'rates')
            write_observations(connection, fixed.to_offer_prices_data_frame(today), 'offer_prices')
            if local.hour == 17:
                def query(sql, params=None):
                    result = execute(connection, sql, params)
                    return pd.DataFrame(result.fetchall(), columns=['timestamp', 'isin', 'spot_price'])
                ohlc = calculate_open_high_low_close_prices(today, query)
                write_observations(connection, ohlc, 'ohlc_prices')
                write_observations(connection, fixed.to_spot_prices_data_frame(stamp), 'closing_prices')
            statuses = []
            for scraper in fixed_scrapers:
                partial_floating = any(s.institute == scraper.institute and (s.missing_observations or not s.scrape_success) for s in floating_scrapers)
                if not scraper.scrape_success:
                    status = Status.NotOK
                elif scraper.missing_observations or partial_floating:
                    status = Status.SomeDataMissing
                elif local.hour == 17:
                    status = Status.ExchangeClosed
                else:
                    status = Status.OK
                has_prices = any(bond.institute == scraper.institute.name and pd.notna(bond.spot_price) for bond in fixed.entries)
                if scraper.scrape_success and not has_prices:
                    status = Status.SomeDataMissing
                statuses.append({'institute': scraper.institute.name, 'timestamp': stamp if has_prices else None, 'status': status.name})
            write_status(connection, statuses)
            if audit.total:
                write_log(connection, stamp, json.dumps({'event': 'scrape_quality', 'warning_count': audit.total, 'messages': audit.messages}, ensure_ascii=False))
        logging.info('Scrape committed: %s, fixed=%d, floating=%d, warnings=%d', stamp, len(fixed.entries), len(floating.entries), audit.total)
        return True
    except Exception as error:
        logging.exception('Scrape failed; database cycle rolled back')
        try:
            with transaction(conn_module) as connection:
                write_log(connection, stamp, json.dumps({'event': 'scrape_failed', 'type': type(error).__name__, 'error': str(error)[:4000], 'messages': audit.messages}, ensure_ascii=False))
        except Exception:
            logging.exception('Could not persist scrape failure; see worker log')
        raise
    finally:
        logging.getLogger().removeHandler(audit)
