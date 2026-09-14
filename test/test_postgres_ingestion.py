"""Optional PostgreSQL integration tests. Only explicit loopback test URLs allowed."""
import json
import os
import unittest
import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from credit_institute_scraper.scrapers.run_scraper import scrape
from test.test_scraper_framework import FixtureSource

TEST_URL = os.environ.get('TEST_POSTGRES_URL')


@unittest.skipUnless(TEST_URL, 'Set TEST_POSTGRES_URL to a disposable local PostgreSQL instance')
class PostgresIngestionTests(unittest.TestCase):
    def setUp(self):
        if make_url(TEST_URL).host not in {'127.0.0.1', 'localhost', '::1'}:
            raise RuntimeError('Integration tests require an explicit loopback database')
        self.schema = 'scraper_test_' + uuid.uuid4().hex
        self.admin = create_engine(TEST_URL, poolclass=NullPool)
        with self.admin.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA {self.schema}'))
        self.module = SimpleNamespace(client_factory=self.factory, query_db=self.query)
        with self.factory().begin() as connection:
            connection.exec_driver_sql('''
                CREATE TABLE master_data (isin text NOT NULL, institute text NOT NULL, years_to_maturity bigint NOT NULL, max_interest_only_period double precision NOT NULL, coupon_rate double precision,
                    CONSTRAINT master_data_product_key UNIQUE(isin,years_to_maturity,max_interest_only_period));
                CREATE UNIQUE INDEX master_data_jyske_isin_key ON master_data(isin) WHERE institute='Jyske';
                CREATE TABLE master_data_float (institute text, fixed_rate_period bigint, max_interest_only_period bigint,
                    CONSTRAINT master_data_float_product_key UNIQUE(institute,fixed_rate_period,max_interest_only_period));
                CREATE TABLE spot_prices (timestamp timestamp, isin text, spot_price double precision);
                CREATE TABLE offer_prices (timestamp timestamp, isin text, offer_price double precision);
                CREATE TABLE closing_prices (timestamp timestamp, isin text, spot_price double precision);
                CREATE TABLE ohlc_prices (timestamp timestamp, isin text, open_price double precision, high_price double precision, low_price double precision, close_price double precision);
                CREATE TABLE rates (timestamp timestamp, institute text, fixed_rate_period bigint, max_interest_only_period text, spot_rate double precision);
                CREATE TABLE status (institute text, last_data_time timestamp, status text);
                CREATE TABLE scrape_logs (time timestamp, error text);
            ''')

    def tearDown(self):
        with self.admin.begin() as connection:
            connection.execute(text(f'DROP SCHEMA {self.schema} CASCADE'))
        self.admin.dispose()

    def factory(self):
        # SET on connect also works with the local PGlite wire-protocol server.
        engine = create_engine(TEST_URL, poolclass=NullPool)
        from sqlalchemy import event
        @event.listens_for(engine, 'connect')
        def set_schema(connection, _record):
            with connection.cursor() as cursor:
                cursor.execute(f'SET search_path TO {self.schema}')
            connection.commit()
        return engine

    def query(self, sql, params=None):
        engine = self.factory()
        try:
            return pd.read_sql(text(sql), engine, params=params)
        finally:
            engine.dispose()

    def cycle(self):
        return scrape(self.module, now=datetime(2026, 9, 14, 7, 2, tzinfo=timezone.utc),
                      fixed_scrapers=[FixtureSource()], floating_scrapers=[FixtureSource()])

    def test_real_driver_cycle_and_retry_are_idempotent(self):
        self.cycle()
        self.cycle()
        for table in ['master_data', 'master_data_float', 'spot_prices', 'offer_prices', 'rates', 'status']:
            self.assertEqual(len(self.query(f'SELECT * FROM {table}')), 1, table)
        self.assertEqual(self.query('SELECT status FROM status').iloc[0, 0], 'OK')

    def test_constraint_failure_rolls_back_cycle_and_retains_failure_audit(self):
        engine = self.factory()
        try:
            with engine.begin() as connection:
                connection.execute(text('ALTER TABLE rates ADD CONSTRAINT simulated_failure CHECK (spot_rate < 0)'))
        finally:
            engine.dispose()
        with self.assertLogs(level='ERROR'), self.assertRaises(Exception):
            self.cycle()
        for table in ['master_data', 'master_data_float', 'spot_prices', 'rates', 'status']:
            self.assertTrue(self.query(f'SELECT * FROM {table}').empty, table)
        event = json.loads(self.query('SELECT error FROM scrape_logs').iloc[0, 0])
        self.assertEqual(event['event'], 'scrape_failed')

    def test_missing_master_migration_stops_writes(self):
        engine = self.factory()
        try:
            with engine.begin() as connection:
                connection.execute(text('DROP INDEX master_data_jyske_isin_key'))
        finally:
            engine.dispose()
        with self.assertLogs(level='ERROR'), self.assertRaisesRegex(RuntimeError, 'migration 001 is missing'):
            self.cycle()
        self.assertTrue(self.query('SELECT * FROM spot_prices').empty)
