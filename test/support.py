"""Fixtures only: explicit loopback PostgreSQL, never application credentials."""

import copy
import json
import os
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

import scraper
from src.credit_institute_scraper import sources

STAMP = datetime(2026, 9, 14, 7, 2, tzinfo=timezone.utc)
ISIN = "DK0009420069"
NORDEA = "DK0002066521"
DIRECTORY = Path(__file__).parent / "fixtures"
PAYLOADS = json.loads((DIRECTORY / "provider_responses.json").read_text(encoding="utf-8"))
EXPECTED = json.loads((DIRECTORY / "expected_products.json").read_text(encoding="utf-8"))
ADAPTERS = {
    "jyske_fixed": ("Jyske", "fixed"),
    "jyske_floating": ("Jyske", "floating"),
    "nordea_fixed": ("Nordea", "fixed"),
    "rd_fixed": ("RealKreditDanmark", "fixed"),
    "rd_floating": ("RealKreditDanmark", "floating"),
    "tk_fixed": ("TotalKredit", "fixed"),
    "tk_floating": ("TotalKredit", "floating"),
}


def payload(institute="Jyske", **changes):
    if institute == "Jyske":
        item = copy.deepcopy(PAYLOADS["jyske_fixed"]["fastRenteProdukter"][0])
        item.update(changes)
        data = {
            "fastRenteProdukter": [item],
            "variabelRenteProdukter": [
                copy.deepcopy(PAYLOADS["jyske_floating"]["variabelRenteProdukter"][0])
            ],
        }
        return {sources.ENDPOINTS[institute][0]: data}
    if institute == "Nordea":
        item = copy.deepcopy(PAYLOADS["nordea_fixed"][0])
        item.update(changes)
        return {sources.ENDPOINTS[institute][0]: [item]}
    prefix = "rd" if institute == "RealKreditDanmark" else "tk"
    return {
        url: copy.deepcopy(PAYLOADS[prefix + "_" + kind])
        for kind, url in zip(("fixed", "floating"), sources.ENDPOINTS[institute])
    }


class DatabaseCase(unittest.TestCase):
    def setUp(self):
        url = os.environ.get("TEST_POSTGRES_URL")
        if not url:
            self.skipTest("Set TEST_POSTGRES_URL to an isolated local PostgreSQL instance")
        if make_url(url).host not in {"localhost", "127.0.0.1", "::1"}:
            raise RuntimeError("Only explicit loopback test databases are permitted")
        self.schema = "scraper_test_" + uuid.uuid4().hex
        self.admin = create_engine(url, poolclass=NullPool)
        with self.admin.begin() as c:
            c.execute(text(f"CREATE SCHEMA {self.schema}"))
        self.engine = create_engine(
            url,
            pool_size=4,
            max_overflow=0,
            pool_pre_ping=True,
            connect_args={"options": f"-c search_path={self.schema} -c statement_timeout=5000"},
        )
        self.addCleanup(self.cleanup_database)
        self.sql("""
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
        """)

    def cleanup_database(self):
        self.engine.dispose()
        with self.admin.begin() as c:
            c.execute(text(f"DROP SCHEMA {self.schema} CASCADE"))
        self.admin.dispose()

    def sql(self, sql, params=None):
        with self.engine.begin() as c:
            c.execute(text(sql), params or {})

    def rows(self, table):
        with self.engine.connect() as c:
            return [dict(row) for row in c.execute(text("SELECT * FROM " + table)).mappings()]

    def cycle(self, institute="Jyske", *, now=STAMP, data=None, **changes):
        data = data if data is not None else payload(institute, **changes)
        with patch.object(scraper.transport, "fetch", AsyncMock(return_value=data)):
            return scraper.run_institute(self.engine, institute, now)
