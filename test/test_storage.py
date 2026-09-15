import json
import unittest
from datetime import datetime

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from src.credit_institute_scraper import sources, storage
from test.support import ISIN, NORDEA, STAMP, DatabaseCase, payload


class DailyQualityTests(unittest.TestCase):
    def test_empty_daily_coverage_requires_rates_except_for_nordea(self):
        for institute, expected in (("Jyske", ["floating.missing"]), ("Nordea", [])):
            with self.subTest(institute=institute):
                issues = storage.daily_issues(
                    [],
                    institute=institute,
                    known_rates=set(),
                    covered_rates=set(),
                    covered_offers=set(),
                )
                self.assertEqual([issue.code for issue in issues], expected)

    def test_daily_coverage_suppresses_only_already_covered_quote_failures(self):
        issues = [
            sources.Issue("floating.fetch", "Request timed out"),
            sources.Issue("floating.spot_rate", "Missing rate", "F3/IO0"),
            sources.Issue("floating.spot_rate", "Missing rate", "F3/IO30"),
            sources.Issue("fixed.offer_price", "Missing offer", ISIN),
            sources.Issue("fixed.offer_price", "Missing offer", NORDEA),
            sources.Issue("floating.product", "Invalid product period"),
            sources.Issue("floating.response", "Unexpected response shape"),
            sources.Issue("fixed.spot_price", "Missing current spot", ISIN),
        ]
        cases = (
            ("partial", {(3, 0)}, [issues[0], issues[2], *issues[4:]], True),
            ("complete", {(3, 0), (3, 30)}, issues[4:], False),
        )
        for name, covered, expected, missing in cases:
            with self.subTest(coverage=name):
                actual = storage.daily_issues(
                    issues,
                    institute="RealKreditDanmark",
                    known_rates={(3, 0), (3, 30)},
                    covered_rates=covered,
                    covered_offers={ISIN},
                )
                self.assertEqual(
                    [issue for issue in actual if issue.code != "floating.missing"], expected
                )
                missing_issues = [issue for issue in actual if issue.code == "floating.missing"]
                self.assertEqual(len(missing_issues), int(missing))
                if missing:
                    self.assertIn("(3, 30)", missing_issues[0].message)

    def test_daily_filter_preserves_input_and_leaves_deduplication_to_final_audit(self):
        issue = sources.Issue("floating.product", "Invalid product period")
        covered = sources.Issue("floating.spot_rate", "Missing rate", "F3/IO0")
        original = [issue, covered, issue]
        actual = storage.daily_issues(
            original,
            institute="Jyske",
            known_rates={(3, 0), (5, 0)},
            covered_rates={(3, 0)},
            covered_offers=set(),
        )
        self.assertEqual(original, [issue, covered, issue])
        self.assertEqual(actual[:-1], [issue, issue])
        self.assertEqual(actual[-1].code, "floating.missing")


class StorageTests(DatabaseCase):
    def test_cycle_is_idempotent_and_preserves_schema(self):
        first = self.cycle()
        second = self.cycle()
        for table in (
            "master_data",
            "master_data_float",
            "spot_prices",
            "offer_prices",
            "rates",
        ):
            self.assertEqual(len(self.rows(table)), 1, table)
        self.assertEqual(first["inserted"], {"spot_prices": 1, "offer_prices": 1, "rates": 1})
        self.assertEqual(second["inserted"], {"spot_prices": 0, "offer_prices": 0, "rates": 0})
        self.assertEqual(second["issues"], 0)
        with self.assertRaises(IntegrityError):
            self.sql("INSERT INTO master_data SELECT * FROM master_data")

    def test_retired_status_table_is_optional_and_existing_rows_are_untouched(self):
        self.sql("INSERT INTO status VALUES ('Jyske','2022-01-03','NotOK')")
        previous = self.rows("status")
        self.cycle()
        self.assertEqual(self.rows("status"), previous)
        self.sql("DROP TABLE status")
        self.assertEqual(self.cycle(now=STAMP.replace(minute=7))["inserted"]["spot_prices"], 1)
        with self.engine.connect() as connection:
            self.assertIsNone(connection.execute(text("SELECT to_regclass('status')")).scalar())

    def test_quality_audit_failure_rolls_back_observations(self):
        self.sql(
            "ALTER TABLE scrape_logs ADD CONSTRAINT reject_quality CHECK (error::json->>'event' <> 'scrape_quality')"
        )
        with self.assertLogs(level="ERROR"), self.assertRaises(IntegrityError):
            self.cycle(aktuelKurs=None)
        self.assertEqual(self.rows("master_data"), [])
        self.assertEqual(self.rows("offer_prices"), [])
        self.assertEqual(self.rows("rates"), [])
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual(audit["event"], "scrape_failed")
        self.assertEqual(audit["stage"], "database")

    def test_transaction_rolls_back_and_failure_audit_survives(self):
        self.sql("ALTER TABLE rates ADD CONSTRAINT reject_rate CHECK (spot_rate < 0)")
        with self.assertLogs(level="ERROR"), self.assertRaises(IntegrityError):
            self.cycle()
        for table in (
            "master_data",
            "master_data_float",
            "spot_prices",
            "offer_prices",
            "rates",
            "status",
        ):
            self.assertEqual(self.rows(table), [], table)
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual((audit["event"], audit["institute"]), ("scrape_failed", "Jyske"))
        self.assertEqual(audit["stage"], "database")
        self.assertEqual(audit["slot"], "2026-09-14T07:00:00")
        self.assertIn("IntegrityError", audit["traceback"])
        self.assertIn("reject_rate", audit["traceback"])

    def test_missing_migration_aborts_writes(self):
        self.sql("DROP INDEX master_data_jyske_isin_key")
        with (
            self.assertLogs(level="ERROR"),
            self.assertRaisesRegex(RuntimeError, "migration 001 is missing"),
        ):
            self.cycle()
        self.assertEqual(self.rows("master_data"), [])
        self.assertEqual(self.rows("spot_prices"), [])

    def test_missing_table_is_never_created(self):
        self.sql("DROP TABLE rates")
        with self.assertLogs(level="ERROR"), self.assertRaises(Exception):
            self.cycle()
        self.assertEqual(self.rows("master_data"), [])
        with self.engine.connect() as c:
            self.assertIsNone(c.execute(text("SELECT to_regclass('rates')")).scalar())

    def test_manual_master_corrections_survive(self):
        self.cycle()
        self.sql("UPDATE master_data SET max_interest_only_period=10")
        with self.assertLogs(level="WARNING"):
            self.cycle(now=STAMP.replace(minute=7))
        self.assertEqual(len(self.rows("master_data")), 1)
        self.assertEqual(self.rows("master_data")[0]["max_interest_only_period"], 10)

    def test_jyske_variants_choose_maximum_observed_io(self):
        data = payload()
        fixed = next(iter(data.values()))["fastRenteProdukter"]
        fixed.extend(
            [
                fixed[0] | {"maxAntalAfdragsfrieAar": 10},
                fixed[0] | {"maxAntalAfdragsfrieAar": 30},
            ]
        )
        with self.assertLogs(level="WARNING") as logs:
            self.cycle(data=data)
        self.assertEqual(len(self.rows("master_data")), 1)
        self.assertEqual(self.rows("master_data")[0]["max_interest_only_period"], 30)
        self.assertEqual(len(self.rows("spot_prices")), 1)
        self.assertIn(ISIN, "\n".join(logs.output))

    def test_nordea_variants_remain_filterable_without_duplicate_quotes(self):
        data = payload("Nordea")
        fixed = next(iter(data.values()))
        fixed.append(fixed[0] | {"loanPeriodMax": "15"})
        result = self.cycle("Nordea", data=data)
        self.assertEqual(result["issues"], 0)
        self.assertEqual(sorted(r["years_to_maturity"] for r in self.rows("master_data")), [15, 20])
        self.assertEqual(len(self.rows("spot_prices")), 1)
        self.assertEqual(self.rows("offer_prices"), [])

    def test_rejected_identity_cannot_create_orphan_prices(self):
        self.cycle()
        with self.assertLogs(level="WARNING"):
            result = self.cycle("Nordea", isinCode=ISIN)
        self.assertEqual(len(self.rows("master_data")), 1)
        self.assertEqual(len(self.rows("spot_prices")), 1)
        self.assertEqual(result["inserted"]["spot_prices"], 0)
        self.assertGreater(result["issues"], 0)

    def test_conflicting_new_identities_are_not_guessed(self):
        for field, value in [("kuponrenteProcent", 5), ("loebetidAar", 20)]:
            data = payload()
            fixed = next(iter(data.values()))["fastRenteProdukter"]
            fixed.append(fixed[0] | {field: value})
            with self.subTest(field=field), self.assertLogs(level="WARNING"):
                self.cycle(data=data)
            self.assertEqual(self.rows("master_data"), [])
            self.assertEqual(self.rows("spot_prices"), [])

    def test_missing_price_preserves_master_and_offer_and_warns_once(self):
        with self.assertLogs(level="WARNING") as logs:
            result = self.cycle(aktuelKurs=None)
        self.assertEqual(result["issues"], 1)
        self.assertEqual(len(logs.output), 1)
        self.assertEqual(len(self.rows("master_data")), 1)
        self.assertEqual(len(self.rows("offer_prices")), 1)
        self.assertEqual(self.rows("spot_prices"), [])
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual(audit["issues"][0]["code"], "fixed.spot_price")

    def test_failed_fetch_keeps_prior_quotes_and_leaves_current_slot_empty(self):
        self.cycle()
        previous = self.rows("spot_prices")
        data = {url: TimeoutError("timeout") for url in sources.ENDPOINTS["Jyske"]}
        with self.assertLogs(level="WARNING"):
            result = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["inserted"]["spot_prices"], 0)
        self.assertEqual(self.rows("spot_prices"), previous)
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertIn("fixed.fetch", [issue["code"] for issue in audit["issues"]])

    def test_conflicting_response_and_duplicate_commit_preserve_prior_quotes(self):
        self.cycle()
        previous = self.rows("spot_prices")
        data = payload()
        fixed = next(iter(data.values()))["fastRenteProdukter"]
        fixed.append(fixed[0] | {"aktuelKurs": 99})
        with self.assertLogs(level="WARNING"):
            result = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["inserted"]["spot_prices"], 0)
        self.assertEqual(self.rows("spot_prices"), previous)
        with self.assertLogs(level="WARNING"):
            self.cycle(aktuelKurs=99)
        self.assertEqual(self.rows("spot_prices")[0]["spot_price"], 98.25)

    def test_first_valid_daily_values_are_retained(self):
        self.cycle()
        data = payload(tilbudsKurs=96, aktuelKurs=99)
        next(iter(data.values()))["variabelRenteProdukter"][0]["vaegtetTilbudskursProcent"] = 3
        result = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["issues"], 0)
        self.assertEqual(self.rows("offer_prices")[0]["offer_price"], 98.1)
        self.assertEqual(self.rows("rates")[0]["spot_rate"], 2.5)
        self.assertEqual(len(self.rows("spot_prices")), 2)

    def test_already_covered_daily_data_does_not_repeat_quality_warnings(self):
        self.cycle()
        data = payload(tilbudsKurs=None)
        floating = next(iter(data.values()))["variabelRenteProdukter"]
        floating[0]["vaegtetTilbudskursProcent"] = None
        result = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["issues"], 0)
        self.assertEqual(len(self.rows("rates")), 1)
        self.assertEqual(self.rows("rates")[0]["spot_rate"], 2.5)

    def test_new_product_with_missing_rate_remains_visible_and_recovers(self):
        self.cycle()
        data = payload()
        floating = next(iter(data.values()))["variabelRenteProdukter"]
        floating.append(floating[0] | {"fastrenteperiode": 5, "vaegtetTilbudskursProcent": None})
        with self.assertLogs(level="WARNING"):
            missing = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(missing["issues"], 2)
        self.assertEqual(
            sorted(r["fixed_rate_period"] for r in self.rows("master_data_float")),
            [3, 5],
        )
        self.assertEqual([r["fixed_rate_period"] for r in self.rows("rates")], [3])
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertIn(
            ("floating.spot_rate", "F5/IO0"),
            [(i["code"], i["product"]) for i in audit["issues"]],
        )
        self.assertIn("floating.missing", [i["code"] for i in audit["issues"]])

        floating[0]["vaegtetTilbudskursProcent"] = 3
        floating[1]["vaegtetTilbudskursProcent"] = 2.75
        recovered = self.cycle(now=STAMP.replace(minute=12), data=data)
        self.assertEqual(recovered["issues"], 0)
        self.assertEqual(
            {r["fixed_rate_period"]: r["spot_rate"] for r in self.rows("rates")},
            {3: 2.5, 5: 2.75},
        )

    def test_missing_rate_is_suppressed_only_for_the_exact_daily_product(self):
        data = payload("RealKreditDanmark")
        fixed_url, floating_url = sources.ENDPOINTS["RealKreditDanmark"]
        data[fixed_url] = data[fixed_url][:1]
        data[floating_url] = data[floating_url][:1]
        self.assertEqual(self.cycle("RealKreditDanmark", data=data)["issues"], 0)
        data[floating_url] = [
            {"name": "FlexLoan_F3_WithInstallment", "offerrate": None},
            {"name": "FlexLoan_F3_WithoutInstallment", "offerrate": None},
        ]
        with self.assertLogs(level="WARNING"):
            result = self.cycle("RealKreditDanmark", now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["issues"], 2)
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual(
            [i["product"] for i in audit["issues"] if i["code"] == "floating.spot_rate"],
            ["F3/IO30"],
        )
        self.assertEqual(len(self.rows("master_data_float")), 2)
        self.assertEqual(len(self.rows("rates")), 1)

    def test_covered_daily_fetch_failure_does_not_repeat_quality_warnings(self):
        data = payload("RealKreditDanmark")
        fixed_url, floating_url = sources.ENDPOINTS["RealKreditDanmark"]
        data[fixed_url] = data[fixed_url][:1]
        self.assertEqual(self.cycle("RealKreditDanmark", data=data)["issues"], 0)
        data[floating_url] = TimeoutError("floating quote request timed out")
        result = self.cycle("RealKreditDanmark", now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["issues"], 0)
        self.assertEqual(len(self.rows("rates")), 2)

    def test_malformed_new_floating_identity_is_not_hidden_by_daily_coverage(self):
        self.cycle()
        data = payload()
        floating = next(iter(data.values()))["variabelRenteProdukter"]
        floating.append(floating[0] | {"fastrenteperiode": "bad"})
        with self.assertLogs(level="WARNING"):
            result = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(result["issues"], 1)
        audit = json.loads(self.rows("scrape_logs")[0]["error"])
        self.assertEqual(audit["issues"][0]["code"], "floating.product")
        self.assertIn("bad", audit["issues"][0]["message"])
        self.assertEqual(len(self.rows("master_data_float")), 1)

    def test_broken_floating_response_is_not_hidden_by_daily_coverage(self):
        self.cycle()
        for index, response in enumerate((None, {}, [])):
            with self.subTest(response=response), self.assertLogs(level="WARNING"):
                data = payload()
                next(iter(data.values()))["variabelRenteProdukter"] = response
                result = self.cycle(now=STAMP.replace(minute=7 + 5 * index), data=data)
                self.assertGreater(result["issues"], 0)
        self.assertEqual(len(self.rows("rates")), 1)

    def test_missing_daily_products_are_recovered_later(self):
        self.sql("INSERT INTO master_data_float VALUES ('Jyske',5,0)")
        with self.assertLogs(level="WARNING"):
            first = self.cycle()
        self.assertEqual(first["issues"], 1)
        data = payload()
        floating = next(iter(data.values()))["variabelRenteProdukter"]
        floating.append(floating[0] | {"fastrenteperiode": 5})
        second = self.cycle(now=STAMP.replace(minute=7), data=data)
        self.assertEqual(second["issues"], 0)
        self.assertEqual(len(self.rows("rates")), 2)

    def test_new_floating_products_are_discovered_after_open(self):
        self.cycle()
        data = payload()
        floating = next(iter(data.values()))["variabelRenteProdukter"]
        floating.append(floating[0] | {"fastrenteperiode": 5})
        self.cycle(now=STAMP.replace(hour=12), data=data)
        self.assertEqual(len(self.rows("master_data_float")), 2)
        self.assertEqual(len(self.rows("rates")), 2)

    def test_other_institutes_bad_history_does_not_pollute_quality_audit(self):
        self.sql(f"INSERT INTO spot_prices VALUES ('2026-09-14 07:00:00','{NORDEA}',NULL)")
        self.sql("INSERT INTO rates VALUES ('2026-09-14','Nordea',3,'bad',NULL)")
        self.assertEqual(self.cycle()["issues"], 0)
        self.assertEqual(self.rows("scrape_logs"), [])

    def test_invalid_existing_quote_is_not_repaired_by_adding_a_duplicate(self):
        self.sql(f"INSERT INTO spot_prices VALUES ('2026-09-14 07:00:00','{ISIN}',NULL)")
        with self.assertLogs(level="WARNING"):
            result = self.cycle()
        self.assertGreater(result["issues"], 0)
        self.assertEqual(result["inserted"]["spot_prices"], 0)
        self.assertEqual(len(self.rows("spot_prices")), 1)

    def test_closing_uses_valid_sorted_rows_scoped_to_institute(self):
        self.sql(f"""
            INSERT INTO master_data VALUES ('{NORDEA}','Nordea',15,0,3.5),('{NORDEA}','Nordea',20,0,3.5);
            INSERT INTO spot_prices VALUES ('2026-09-14 11:00:00','{ISIN}',100),
                ('2026-09-14 07:00:00','{ISIN}',96),('2026-09-14 07:00:00','{NORDEA}',93),
                ('2026-09-14 06:00:00','{ISIN}',NULL);
        """)
        with self.assertLogs(level="WARNING"):
            self.cycle(now=STAMP.replace(hour=15, minute=0))
        candle = self.rows("ohlc_prices")[0]
        self.assertEqual(
            (
                candle["open_price"],
                candle["high_price"],
                candle["low_price"],
                candle["close_price"],
            ),
            (96, 100, 96, 98.25),
        )
        self.assertEqual([r["isin"] for r in self.rows("closing_prices")], [ISIN])
        self.assertEqual(len(self.rows("ohlc_prices")), 1)

    def test_ohlc_never_overwrites_existing_history(self):
        self.cycle(now=STAMP.replace(hour=15, minute=0))
        before = self.rows("ohlc_prices")
        self.sql(f"INSERT INTO spot_prices VALUES ('2026-09-14 07:00:00','{ISIN}',96)")
        with self.assertLogs(level="WARNING"):
            self.cycle(now=STAMP.replace(hour=15, minute=0))
        self.assertEqual(self.rows("ohlc_prices"), before)

    def test_validation_protects_all_observation_tables(self):
        stamp = datetime(2026, 9, 14, 7)
        for table in storage.VALUES:
            base = dict(
                timestamp=stamp,
                isin=ISIN,
                institute="Jyske",
                fixed_rate_period=3,
                max_interest_only_period=0,
            )
            base.update({k: 98 for k in storage.VALUES[table]})
            for invalid in (0, True, float("nan"), float("inf")):
                with (
                    self.subTest(table=table, invalid=invalid),
                    self.engine.begin() as c,
                ):
                    issue = []
                    record = base | {storage.VALUES[table][0]: invalid}
                    count, observations = storage.write(
                        c,
                        table,
                        [record],
                        stamp,
                        stamp,
                        ["Jyske"] if table == "rates" else [ISIN],
                        issue,
                    )
                    self.assertEqual((count, observations), (0, {}))
                    self.assertTrue(issue)

    def test_inconsistent_ohlc_bounds_are_rejected(self):
        record = dict(
            timestamp=datetime(2026, 9, 14),
            isin=ISIN,
            open_price=98,
            close_price=99,
            low_price=100,
            high_price=101,
        )
        issues = []
        self.assertEqual(storage.clean([record], "ohlc_prices", issues), {})
        self.assertEqual(len(issues), 1)

    def test_floating_master_keys_normalize_text_and_preserve_io_variants(self):
        rows = [
            dict(institute="Jyske", fixed_rate_period="3", max_interest_only_period=v)
            for v in ("0", 0.0, "10", "30")
        ]
        issues = []
        clean = storage.normalize_master(rows, "master_data_float", issues)
        self.assertEqual([r["max_interest_only_period"] for r in clean], [0, 10, 30])
        self.assertEqual(issues, [])
        products = [sources.rate("Jyske", 3, r["max_interest_only_period"], 2.5) for r in clean]
        with self.engine.begin() as c:
            storage.insert_master(c, products, "Jyske", issues)
        self.assertEqual(len(self.rows("master_data_float")), 3)

    def test_invalid_master_values_are_rejected_without_deleting_data(self):
        self.cycle()
        stored = self.rows("master_data")
        issues = []
        self.assertEqual(
            storage.normalize_master(
                [stored[0] | {"isin": None}, stored[0] | {"coupon_rate": float("nan")}],
                "master_data",
                issues,
            ),
            [],
        )
        self.assertEqual(len(issues), 2)
        self.assertEqual(self.rows("master_data"), stored)

    def test_engine_reuses_connections_across_transactions(self):
        self.cycle()
        self.cycle(now=STAMP.replace(minute=7))
        self.assertEqual(self.engine.pool.checkedout(), 0)
        self.assertEqual(self.engine.pool.checkedin(), 1)
