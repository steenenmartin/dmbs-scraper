import json
import sqlite3
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pandas as pd
import requests
from sqlalchemy import create_engine, text

from credit_institute_scraper.bond_data.fixed_rate_bond_data_entry import FixedRateBondDataEntry
from credit_institute_scraper.bond_data.floating_rate_bond_data_entry import FloatingRateBondDataEntry
from credit_institute_scraper.database.ingestion import prepare_observations, transaction, write_observations
from credit_institute_scraper.database.load_data import calculate_open_high_low_close_prices
from credit_institute_scraper.enums.credit_insitute import CreditInstitute
from credit_institute_scraper.scrapers.scraper import Scraper
from credit_institute_scraper.scrapers.scraper_orchestrator import ScraperOrchestrator
from credit_institute_scraper.scrapers.run_scraper import scrape
from credit_institute_scraper.utils.date_helper import is_holiday, get_active_time_range

STAMP = datetime(2026, 9, 14, 7, 2, tzinfo=timezone.utc)
ISIN = 'DK0009420069'


class FixtureSource(Scraper):
    institute = CreditInstitute.Jyske
    url = 'https://example.invalid/feed'

    def get_data(self):
        return {}

    @Scraper.scraper
    def parse_fixed_rate_bonds(self, data):
        return [FixedRateBondDataEntry('Jyske', 30, 98, 97, 0, 4, ISIN)]

    @Scraper.scraper
    def parse_floating_rate_bonds(self, data):
        return [FloatingRateBondDataEntry('Jyske', 3, 0, 2.5)]


class FrameworkTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.path = str(Path(self.directory.name) / 'fixture.db')
        self.url = 'sqlite:///' + self.path
        self.module = SimpleNamespace(client_factory=lambda: create_engine(self.url), query_db=self.query)
        self.run_sql('''
            CREATE TABLE master_data (isin TEXT, institute TEXT, years_to_maturity INTEGER, max_interest_only_period INTEGER, coupon_rate REAL, UNIQUE(isin,years_to_maturity,max_interest_only_period));
            CREATE UNIQUE INDEX master_data_jyske_isin_key ON master_data(isin) WHERE institute='Jyske';
            CREATE TABLE master_data_float (institute TEXT, fixed_rate_period INTEGER, max_interest_only_period INTEGER, UNIQUE(institute,fixed_rate_period,max_interest_only_period));
            CREATE TABLE spot_prices (timestamp TIMESTAMP, isin TEXT, spot_price REAL);
            CREATE TABLE offer_prices (timestamp TIMESTAMP, isin TEXT, offer_price REAL);
            CREATE TABLE closing_prices (timestamp TIMESTAMP, isin TEXT, spot_price REAL);
            CREATE TABLE ohlc_prices (timestamp TIMESTAMP, isin TEXT, open_price REAL, high_price REAL, low_price REAL, close_price REAL);
            CREATE TABLE rates (timestamp TIMESTAMP, institute TEXT, fixed_rate_period INTEGER, max_interest_only_period TEXT, spot_rate REAL);
            CREATE TABLE status (institute TEXT, last_data_time TIMESTAMP, status TEXT);
            CREATE TABLE scrape_logs (time TIMESTAMP, error TEXT);
        ''')

    def tearDown(self):
        self.directory.cleanup()

    def run_sql(self, sql):
        connection = sqlite3.connect(self.path)
        try:
            connection.executescript(sql)
        finally:
            connection.close()

    def query(self, sql, params=None):
        engine = create_engine(self.url)
        try:
            return pd.read_sql(text(sql), engine, params=params)
        finally:
            engine.dispose()

    def run_cycle(self, **kwargs):
        return scrape(self.module, now=STAMP, fixed_scrapers=[FixtureSource()], floating_scrapers=[FixtureSource()], **kwargs)

    def test_whole_cycle_is_idempotent_and_preserves_schema(self):
        self.run_cycle()
        self.run_cycle()
        for table in ['master_data', 'master_data_float', 'spot_prices', 'offer_prices', 'rates', 'status']:
            self.assertEqual(len(self.query(f'SELECT * FROM {table}')), 1, table)
        self.assertEqual(self.query('SELECT spot_price FROM spot_prices').iloc[0, 0], 98)
        self.assertEqual(self.query('SELECT status FROM status').iloc[0, 0], 'OK')
        self.assertEqual(len(self.query("SELECT * FROM sqlite_master WHERE name='master_data_jyske_isin_key'")), 1)

    def test_failure_rolls_back_all_data_and_persists_failure_audit(self):
        self.run_sql("CREATE TRIGGER reject_rate BEFORE INSERT ON rates BEGIN SELECT RAISE(ABORT, 'simulated failure'); END;")
        with self.assertLogs(level='ERROR'), self.assertRaises(Exception):
            self.run_cycle()
        for table in ['master_data', 'master_data_float', 'spot_prices', 'rates', 'offer_prices', 'status']:
            self.assertTrue(self.query(f'SELECT * FROM {table}').empty, table)
        event = json.loads(self.query('SELECT error FROM scrape_logs').iloc[0, 0])
        self.assertEqual(event['event'], 'scrape_failed')
        self.assertIn('simulated failure', event['error'])

    def test_empty_source_retries_are_bounded_and_persist_failed_status(self):
        source = FixtureSource()
        source.get_data = Mock(side_effect=requests.Timeout('feed timed out'))
        with patch('credit_institute_scraper.scrapers.scraper_orchestrator.time.sleep'):
            # Inject the backoff into the orchestrator, avoiding real test delays.
            with patch('credit_institute_scraper.scrapers.run_scraper.ScraperOrchestrator', side_effect=lambda sources: ScraperOrchestrator(sources, sleep=lambda _: None)):
                with self.assertLogs(level='WARNING'):
                    scrape(self.module, now=STAMP, fixed_scrapers=[source], floating_scrapers=[])
        self.assertEqual(source.get_data.call_count, 3)
        self.assertTrue(self.query('SELECT * FROM spot_prices').empty)
        self.assertEqual(self.query('SELECT status FROM status').iloc[0, 0], 'NotOK')
        self.assertIn('feed timed out', self.query('SELECT error FROM scrape_logs').iloc[0, 0])

    def test_missing_daily_products_are_retried_after_open(self):
        self.run_cycle()
        self.run_sql("INSERT INTO master_data_float VALUES ('Jyske',5,0)")
        floating = FixtureSource()
        floating.parse_floating_rate_bonds = Mock(return_value=[FloatingRateBondDataEntry('Jyske', 5, 0, 2.75)])
        scrape(self.module, now=STAMP.replace(hour=10), fixed_scrapers=[], floating_scrapers=[floating])
        floating.parse_floating_rate_bonds.assert_called_once()
        self.assertEqual(len(self.query('SELECT * FROM rates')), 2)

    def test_bad_new_master_identity_does_not_create_orphan_prices(self):
        source = FixtureSource()
        source.parse_fixed_rate_bonds = Mock(return_value=[
            FixedRateBondDataEntry('Jyske', 30, 98, 97, 0, coupon, ISIN) for coupon in (4, 5)])
        with self.assertLogs(level='WARNING'):
            scrape(self.module, now=STAMP, fixed_scrapers=[source], floating_scrapers=[])
        self.assertTrue(self.query('SELECT * FROM master_data').empty)
        self.assertTrue(self.query('SELECT * FROM spot_prices').empty)
        self.assertIn('master identity', self.query('SELECT error FROM scrape_logs').iloc[0, 0])

    def test_failed_source_does_not_advance_last_data_time(self):
        self.run_cycle()
        before = self.query('SELECT last_data_time FROM status').iloc[0, 0]
        source = FixtureSource()
        source.get_data = Mock(side_effect=ValueError('bad response'))
        with patch('credit_institute_scraper.scrapers.run_scraper.ScraperOrchestrator', side_effect=lambda sources: ScraperOrchestrator(sources, sleep=lambda _: None)):
            with self.assertLogs(level='WARNING'):
                scrape(self.module, now=STAMP.replace(hour=8), fixed_scrapers=[source], floating_scrapers=[])
        status = self.query('SELECT * FROM status').iloc[0]
        self.assertEqual(status.last_data_time, before)
        self.assertEqual(status.status, 'NotOK')

    def test_silently_missing_daily_product_is_audited(self):
        self.run_sql("INSERT INTO master_data_float VALUES ('Jyske',5,0)")
        with self.assertLogs(level='WARNING'):
            self.run_cycle()
        self.assertEqual(self.query('SELECT status FROM status').iloc[0, 0], 'SomeDataMissing')
        self.assertIn('Missing known floating products', self.query('SELECT error FROM scrape_logs').iloc[0, 0])

    def test_weekend_and_outside_market_hours_do_not_connect(self):
        module = SimpleNamespace(query_db=Mock(side_effect=AssertionError('Unexpected database access')))
        for instant in [STAMP.replace(day=12), STAMP.replace(hour=5), STAMP.replace(hour=16)]:
            self.assertFalse(scrape(module, now=instant))
        module.query_db.assert_not_called()

    def test_conflicting_prices_are_rejected_and_previous_observations_survive(self):
        frame = pd.DataFrame([{'timestamp': STAMP, 'isin': ISIN, 'spot_price': value} for value in (98, 99)])
        with self.assertLogs(level='WARNING'):
            self.assertTrue(prepare_observations(frame, 'spot_prices').empty)
        with transaction(self.module) as conn:
            self.assertEqual(write_observations(conn, frame.iloc[:1], 'spot_prices'), 1)
        with transaction(self.module) as conn, self.assertLogs(level='WARNING'):
            self.assertEqual(write_observations(conn, frame.iloc[1:], 'spot_prices'), 0)
        self.assertEqual(self.query('SELECT spot_price FROM spot_prices').iloc[0, 0], 98)

    def test_missing_table_is_not_created(self):
        self.run_sql('DROP TABLE spot_prices')
        frame = pd.DataFrame([{'timestamp': STAMP, 'isin': ISIN, 'spot_price': 98}])
        with self.assertRaises(Exception), transaction(self.module) as conn:
            write_observations(conn, frame, 'spot_prices')
        self.assertTrue(self.query("SELECT * FROM sqlite_master WHERE name='spot_prices'").empty)

    def test_sqlite_connection_path_commits_and_rolls_back(self):
        module = SimpleNamespace(client_factory=lambda: sqlite3.connect(self.path))
        frame = pd.DataFrame([{'timestamp': STAMP, 'isin': ISIN, 'spot_price': 98}])
        with transaction(module) as conn:
            write_observations(conn, frame, 'spot_prices')
        with self.assertRaises(RuntimeError), transaction(module) as conn:
            write_observations(conn, frame.assign(timestamp=STAMP.replace(minute=7)), 'spot_prices')
            raise RuntimeError('rollback')
        self.assertEqual(len(self.query('SELECT * FROM spot_prices')), 1)

    def test_close_uses_sorted_valid_prices_and_includes_final_observation(self):
        self.run_sql(f"INSERT INTO spot_prices VALUES ('2026-09-14 09:00:00','{ISIN}',100), ('2026-09-14 07:00:00','{ISIN}',96), ('2026-09-14 06:00:00','{ISIN}',NULL)")
        with self.assertLogs(level='WARNING'):
            scrape(self.module, now=STAMP.replace(hour=15, minute=0), fixed_scrapers=[FixtureSource()], floating_scrapers=[])
        candle = self.query('SELECT * FROM ohlc_prices').iloc[0]
        self.assertEqual((candle.open_price, candle.high_price, candle.low_price, candle.close_price), (96, 100, 96, 98))
        self.assertEqual(len(self.query('SELECT * FROM closing_prices')), 1)


class SourceSafetyTests(unittest.TestCase):
    def test_all_fixed_adapters_isolate_malformed_products(self):
        from credit_institute_scraper.scrapers.jyske_scraper import JyskeScraper
        from credit_institute_scraper.scrapers.nordea_scraper import NordeaScraper
        from credit_institute_scraper.scrapers.realkredit_danmark_fixed_scraper import RealKreditDanmarkFixedScraper
        from credit_institute_scraper.scrapers.total_kredit_fixed_scraper import TotalKreditFixedScraper
        from credit_institute_scraper.scrapers.dlr_kredit_scraper import DlrKreditScraper
        cases = [
            (JyskeScraper(), {'fastRenteProdukter': [{}, {'loebetidAar': 30, 'aktuelKurs': 98, 'tilbudsKurs': 97, 'maxAntalAfdragsfrieAar': 0, 'kuponrenteProcent': 4, 'isin': ISIN}]}),
            (NordeaScraper(), [{}, {'loanPeriodMax': 20, 'rate': '98,00', 'repaymentFreedomMax': 'Nej', 'fundName': '3,5% 2049', 'isinCode': 'DK0002066521'}]),
            (RealKreditDanmarkFixedScraper(), [{}, {'termToMaturityYears': 30, 'isinCode': ISIN, 'loanTypeCode': '01', 'numberOfTermsWithoutRepayment': 40, 'prices': [{'price': '98,00'}], 'offerprice': 97, 'nominelInterestRate': 4}]),
            (TotalKreditFixedScraper(), {'groups': [{'entries': [{}, {'lifetime': '30 år', 'spotPriceRatePayment': '98,00', 'priceRate': '97,00', 'name': '4% med afdrag', 'fondCode': '942006'}]}]}),
            (DlrKreditScraper(), {'obligationer': [{}, {'loebetid': 30, 'kurs': 97, 'afdragsfrihed': '', 'navn': '4%', 'ISIN': ISIN, 'laanbeskrivelse': 'Fastforrentede obligationslån'}]}),
        ]
        for source, payload in cases:
            with self.subTest(source=type(source).__name__):
                source.get_data = Mock(return_value=payload)
                with self.assertLogs(level='WARNING'):
                    bonds = source.parse_fixed_rate_bonds()
                self.assertEqual(len(bonds), 1)
                self.assertTrue(source.missing_observations)

    def test_holidays_cover_year_rollover_and_whit_monday(self):
        from datetime import date, timedelta
        expected = {
            2026: ['01-01', '04-02', '04-03', '04-06', '05-14', '05-15', '05-25', '06-05', '12-24', '12-25', '12-31'],
            2027: ['01-01', '03-25', '03-26', '03-29', '05-06', '05-07', '05-17', '12-24', '12-31'],
        }
        for year, dates in expected.items():
            days = [date(year, 1, 1) + timedelta(days=offset) for offset in range(365)]
            actual = [day.strftime('%m-%d') for day in days if day.weekday() < 5 and is_holiday(day)]
            self.assertEqual(actual, dates)
        start, end = get_active_time_range(datetime(2026, 5, 25, 12, tzinfo=timezone.utc), force_9_17=True)
        self.assertEqual(start, datetime(2026, 5, 22, 7, tzinfo=timezone.utc))
        self.assertEqual(end, datetime(2026, 5, 22, 15, tzinfo=timezone.utc))

    def test_schedule_follows_danish_dst_without_import_side_effects(self):
        import scraper as worker
        with patch.object(worker, 'BlockingScheduler') as scheduler:
            worker.main()
        self.assertEqual(scheduler.call_args.kwargs['timezone'], 'Europe/Copenhagen')
        from apscheduler.triggers.cron import CronTrigger
        triggers = [
            CronTrigger(day_of_week=call.kwargs['day_of_week'], hour=call.kwargs['hour'],
                        minute=call.kwargs['minute'], timezone='Europe/Copenhagen')
            for call in scheduler.return_value.add_job.call_args_list
        ]
        for instant, hour in [(datetime(2026, 9, 14, 0, tzinfo=timezone.utc), 7), (datetime(2026, 11, 2, 0, tzinfo=timezone.utc), 8)]:
            with self.subTest(day=instant.date()):
                runs = []
                for trigger in triggers:
                    next_run = trigger.get_next_fire_time(None, instant)
                    while next_run.astimezone(timezone.utc).date() == instant.date():
                        runs.append(next_run.astimezone(timezone.utc))
                        next_run = trigger.get_next_fire_time(next_run, next_run + timedelta(seconds=1))
                opening = instant.replace(hour=hour)
                expected = [opening + timedelta(minutes=2)] + [
                    opening + timedelta(minutes=minute) for minute in range(5, 481, 5)
                ]
                self.assertEqual(sorted(runs), expected)
        saturday = datetime(2026, 9, 12, tzinfo=timezone.utc)
        for trigger in triggers:
            self.assertEqual(trigger.get_next_fire_time(None, saturday).date(), STAMP.date())

    def test_http_status_checked_before_json_and_connections_closed(self):
        source = FixtureSource()
        response = Mock()
        response.raise_for_status.side_effect = requests.HTTPError('503')
        session = Mock()
        session.get.return_value.__enter__ = Mock(return_value=response)
        session.get.return_value.__exit__ = Mock(return_value=False)
        session_context = Mock()
        session_context.__enter__ = Mock(return_value=session)
        session_context.__exit__ = Mock(return_value=False)
        with patch('credit_institute_scraper.scrapers.scraper.requests.Session', return_value=session_context):
            with self.assertRaises(requests.HTTPError):
                Scraper.get_data(source)
        response.json.assert_not_called()
        self.assertEqual(session.get.call_args.kwargs['timeout'], (5, 20))
        session_context.__exit__.assert_called_once()

    def test_bad_product_does_not_discard_valid_siblings(self):
        from credit_institute_scraper.scrapers.realkredit_danmark_floating_scraper import RealKreditDanmarkFloatingScraper
        source = RealKreditDanmarkFloatingScraper()
        source.get_data = Mock(return_value=[{'name': 'FlexLoan_F3_WithInstallment'},
                                            {'name': 'FlexLoan_F5_WithInstallment', 'offerrate': '2.5'},
                                            {'name': 'FlexLoan_F1_WithInstallment', 'offerrate': 'NaN'}])
        with self.assertLogs(level='WARNING'):
            data = source.parse_floating_rate_bonds()
        self.assertEqual([(row.fixed_rate_period, row.spot_rate) for row in data], [(5, 2.5)])
        self.assertTrue(source.missing_observations)
        self.assertEqual(len(source.issues), 2)

    def test_reused_scraper_resets_state_and_backoff_is_bounded(self):
        source = FixtureSource()
        source.get_data = Mock(side_effect=[requests.Timeout(), {}, {}])
        sleep = Mock()
        orchestrator = ScraperOrchestrator([source], sleep=sleep)
        with self.assertLogs(level='WARNING'):
            self.assertEqual(len(orchestrator.scrape_fixed_rate_bonds().entries), 1)
        sleep.assert_called_once_with(1)
        self.assertEqual(len(orchestrator.scrape_floating_rate_bonds().entries), 1)
        self.assertEqual(source.tries_count, 1)
        self.assertFalse(source.missing_observations)

    def test_broken_adapter_cannot_cause_infinite_retries(self):
        source = FixtureSource()
        source.parse_fixed_rate_bonds = Mock(side_effect=ValueError('broken'))
        with self.assertLogs(level='WARNING'):
            result = ScraperOrchestrator([source], sleep=lambda _: None).scrape_fixed_rate_bonds()
        self.assertEqual(result.entries, [])
        self.assertEqual(source.parse_fixed_rate_bonds.call_count, 3)

    def test_invalid_observation_values_are_not_written(self):
        for value in (0, -1, float('inf'), float('nan'), None, True):
            with self.subTest(value=value), self.assertLogs(level='WARNING'):
                frame = pd.DataFrame([{'timestamp': STAMP, 'isin': ISIN, 'spot_price': value}])
                self.assertTrue(prepare_observations(frame, 'spot_prices').empty)
        frame = pd.DataFrame([{'timestamp': STAMP, 'isin': ISIN, 'open_price': 100, 'high_price': 90, 'low_price': 80, 'close_price': 85}])
        with self.assertLogs(level='WARNING'):
            self.assertTrue(prepare_observations(frame, 'ohlc_prices').empty)


if __name__ == '__main__':
    unittest.main()
