"""Failures reproduced while pressure-testing the first pipeline refactor."""

import copy
import json
import unittest
from pathlib import Path

from src.credit_institute_scraper.sources import parse
from test.support import ISIN, STAMP, DatabaseCase


class ParserRegressionTests(unittest.TestCase):
    def product(self, **changes):
        fixtures = json.loads(
            (Path(__file__).parent / "fixtures/provider_responses.json").read_text()
        )
        item = copy.deepcopy(fixtures["jyske_fixed"]["fastRenteProdukter"][0])
        item.update(changes)
        return parse("Jyske", "fixed", {"fastRenteProdukter": [item]})[0]

    def test_null_price_keeps_master_and_other_price(self):
        parsed = self.product(aktuelKurs=None)
        self.assertEqual(len(parsed), 1)
        self.assertIsNone(parsed[0].spot_price)
        self.assertEqual(parsed[0].offer_price, 98.1)

    def test_boolean_price_is_not_a_quote(self):
        parsed = self.product(aktuelKurs=True)
        self.assertEqual(len(parsed), 1)
        self.assertIsNone(parsed[0].spot_price)

    def test_fractional_term_is_not_truncated(self):
        self.assertEqual(self.product(loebetidAar=30.9), [])


class DatabaseRegressionTests(DatabaseCase):
    def test_delayed_commit_preserves_later_observation(self):
        self.cycle(now=STAMP.replace(hour=8, minute=0))
        before = self.rows("spot_prices")[0]
        self.cycle(now=STAMP.replace(hour=7, minute=0))
        observations = self.rows("spot_prices")
        self.assertIn(before, observations)
        self.assertEqual(len(observations), 2)
        self.assertEqual(max(row["timestamp"] for row in observations), before["timestamp"])

    def test_closing_uses_stored_spot_when_incoming_spot_conflicts(self):
        self.sql(f"INSERT INTO spot_prices VALUES ('2026-09-14 15:00:00','{ISIN}',99)")
        self.cycle(now=STAMP.replace(hour=15, minute=0))
        self.assertEqual(self.rows("closing_prices")[0]["spot_price"], 99)
        self.assertEqual(self.rows("ohlc_prices")[0]["close_price"], 99)
