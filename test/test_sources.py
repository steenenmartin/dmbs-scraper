import copy
import unittest
from dataclasses import FrozenInstanceError, asdict
from unittest.mock import Mock, patch

from src.credit_institute_scraper import sources
from test.support import ADAPTERS, EXPECTED, PAYLOADS


class SourceTests(unittest.TestCase):
    def test_all_seven_formats_match_baseline(self):
        for key, (institute, kind) in ADAPTERS.items():
            with self.subTest(key=key):
                entries, _ = sources.parse(institute, kind, PAYLOADS[key])
                quoted = [
                    p for p in entries if not isinstance(p, sources.Rate) or p.spot_rate is not None
                ]
                self.assertEqual([asdict(p) for p in quoted], EXPECTED[key])

    def test_malformed_siblings_do_not_discard_good_products(self):
        for key, (institute, kind) in ADAPTERS.items():
            with self.subTest(key=key):
                data = copy.deepcopy(PAYLOADS[key])
                products = (
                    data
                    if isinstance(data, list)
                    else (
                        data["groups"][0]["entries"]
                        if institute == "TotalKredit"
                        else next(iter(data.values()))
                    )
                )
                products.extend([{}, None])
                actual, issues = sources.parse(institute, kind, data)
                expected, _ = sources.parse(institute, kind, PAYLOADS[key])
                self.assertEqual(actual, expected)
                self.assertGreaterEqual(len(issues), 2)

    def test_missing_rates_keep_identity_and_negative_rates_are_preserved(self):
        for value in (None, "", "unavailable", 0, float("nan"), float("inf"), True):
            with self.subTest(value=value):
                self.assertEqual(
                    sources.rate("Jyske", 3, 0, value),
                    sources.Rate("Jyske", 3, 0, None),
                )
        self.assertEqual(sources.rate("Jyske", 3, 0, -0.2).spot_rate, -0.2)

    def test_missing_floating_quotes_report_field_value_and_product(self):
        cases = (
            ("Jyske", "jyske_floating", "vaegtetTilbudskursProcent", "F3/IO0"),
            ("RealKreditDanmark", "rd_floating", "offerrate", "F3/IO0"),
            ("TotalKredit", "tk_floating", "innerInterestGrossValue", "F3/IO0"),
        )
        for institute, key, field, identity in cases:
            for absent in (False, True):
                with self.subTest(institute=institute, absent=absent):
                    data = copy.deepcopy(PAYLOADS[key])
                    products = (
                        data
                        if isinstance(data, list)
                        else (
                            data["groups"][0]["entries"]
                            if institute == "TotalKredit"
                            else data["variabelRenteProdukter"]
                        )
                    )
                    if absent:
                        del products[0][field]
                    else:
                        products[0][field] = None
                    entries, issues = sources.parse(institute, "floating", data)
                    self.assertEqual(entries[0], sources.Rate(institute, 3, 0, None))
                    issue = next(item for item in issues if item.product == identity)
                    self.assertEqual(issue.code, "floating.spot_rate")
                    self.assertIn(field + "=None", issue.message)

    def test_malformed_metadata_identifies_field_value_and_isin(self):
        data = copy.deepcopy(PAYLOADS["nordea_fixed"])
        data[0]["fundName"] = None
        entries, issues = sources.parse("Nordea", "fixed", data)
        self.assertEqual(len(entries), 2)
        self.assertEqual(len(issues), 1)
        self.assertEqual(issues[0].code, "fixed.product")
        self.assertEqual(issues[0].product, "DK0002066521")
        self.assertIn("fundName=None", issues[0].message)

    def test_missing_price_identifies_source_field_value_and_isin(self):
        data = copy.deepcopy(PAYLOADS["nordea_fixed"])
        data[0]["rate"] = "unavailable"
        entries, issues = sources.parse("Nordea", "fixed", data)
        self.assertIsNone(entries[0].spot_price)
        self.assertEqual(issues[0].product, "DK0002066521")
        self.assertIn("rate='unavailable'", issues[0].message)

    def test_rd_unavailable_spot_marker_keeps_offer_without_parser_warning(self):
        for marker in (-1, -1.0, "-1", "-1.0", "-1,0000", " -1.0000 "):
            with self.subTest(marker=marker):
                product = copy.deepcopy(PAYLOADS["rd_fixed"][0])
                product.update(prices=[{"price": marker}], offerprice="64,55")
                entries, issues = sources.parse("RealKreditDanmark", "fixed", [product])
                self.assertEqual(len(entries), 1)
                self.assertIsNone(entries[0].spot_price)
                self.assertEqual(entries[0].offer_price, 64.55)
                self.assertEqual(issues, [])

    def test_rd_unavailable_offer_marker_preserves_existing_spot_omission_rule(self):
        for marker in (-1, -1.0, "-1", "-1.0", "-1,0000", " -1.0000 "):
            with self.subTest(marker=marker):
                product = copy.deepcopy(PAYLOADS["rd_fixed"][0])
                product.update(prices=[{"price": 98.25}], offerprice=marker)
                entries, issues = sources.parse("RealKreditDanmark", "fixed", [product])
                self.assertIsNone(entries[0].spot_price)
                self.assertIsNone(entries[0].offer_price)
                self.assertEqual(issues, [])

    def test_rd_sentinel_does_not_hide_malformed_sibling_quote(self):
        for value in (None, "", "unavailable", -2, 0, True, float("nan"), float("inf")):
            for quote in ("spot_price", "offer_price"):
                with self.subTest(value=value, quote=quote):
                    product = copy.deepcopy(PAYLOADS["rd_fixed"][0])
                    product.update(
                        prices=[{"price": value if quote == "spot_price" else "-1,0000"}],
                        offerprice=value if quote == "offer_price" else "-1,0000",
                    )
                    entries, issues = sources.parse("RealKreditDanmark", "fixed", [product])
                    self.assertEqual(len(entries), 1)
                    self.assertEqual(len(issues), 1)
                    self.assertEqual(issues[0].code, "fixed." + quote)
                    self.assertEqual(issues[0].product, product["isinCode"])
                    self.assertIn(repr(value), issues[0].message)

    def test_negative_one_remains_a_quote_issue_for_other_providers(self):
        product = copy.deepcopy(PAYLOADS["nordea_fixed"][0])
        product["rate"] = "-1,0000"
        _, issues = sources.parse("Nordea", "fixed", [product])
        self.assertEqual([issue.code for issue in issues], ["fixed.spot_price"])

    def test_unexpected_parser_exceptions_propagate(self):
        for error_type in (TypeError, AttributeError, KeyError, ValueError):
            failure = error_type("parser implementation bug")
            with (
                self.subTest(error=error_type),
                patch.dict(sources.PARSERS, {"Nordea": Mock(side_effect=failure)}),
                self.assertRaises(error_type) as raised,
            ):
                sources.parse("Nordea", "fixed", PAYLOADS["nordea_fixed"])
            self.assertIs(raised.exception, failure)
            self.assertEqual(
                failure.__notes__,
                ["Parsing Nordea fixed: product='DK0002066521', index=0"],
            )

    def test_invalid_json_field_types_are_input_errors_not_parser_crashes(self):
        for key, (institute, kind) in ADAPTERS.items():
            original = PAYLOADS[key]
            products = (
                original
                if isinstance(original, list)
                else (
                    original["groups"][0]["entries"]
                    if institute == "TotalKredit"
                    else next(iter(original.values()))
                )
            )
            for name in products[0]:
                for value in (None, [], {}, True, ""):
                    with self.subTest(provider=key, field=name, value=value):
                        item = dict(products[0], **{name: value})
                        data = (
                            [item]
                            if isinstance(original, list)
                            else (
                                {"groups": [{"entries": [item]}]}
                                if institute == "TotalKredit"
                                else {next(iter(original)): [item]}
                            )
                        )
                        sources.parse(institute, kind, data)

    def test_metadata_rejects_invalid_periods_and_identity(self):
        valid = ["Jyske", 30, 98, 97, 0, 4, "DK0009420069"]
        for index, value in [
            (1, 0),
            (1, 30.2),
            (1, True),
            (4, -1),
            (4, 31),
            (4, 2.5),
            (5, float("nan")),
            (5, True),
            (6, None),
            (6, "bad"),
        ]:
            values = valid.copy()
            values[index] = value
            with (
                self.subTest(index=index, value=value),
                self.assertRaises((ValueError, TypeError)),
            ):
                sources.bond(*values)

    def test_periods_outside_database_integer_range_keep_good_siblings(self):
        cases = (
            ("jyske_fixed", "loebetidAar", 1e300, "years_to_maturity"),
            (
                "jyske_fixed",
                "maxAntalAfdragsfrieAar",
                "1e300",
                "max_interest_only_period",
            ),
            ("jyske_floating", "fastrenteperiode", 1e300, "fixed_rate_period"),
            ("nordea_fixed", "loanPeriodMax", "1e300", "loanPeriodMax"),
            (
                "nordea_fixed",
                "repaymentFreedomMax",
                "1e300",
                "max_interest_only_period",
            ),
            ("rd_fixed", "termToMaturityYears", "1e300", "termToMaturityYears"),
            (
                "rd_fixed",
                "numberOfTermsWithoutRepayment",
                1e300,
                "max_interest_only_period",
            ),
            ("tk_fixed", "lifetime", "1e300 år", "lifetime"),
            (
                "tk_fixed",
                "name",
                "4% lån med op til 100000000000000000000 års afdragsfrihed",
                "name",
            ),
            (
                "tk_floating",
                "name",
                "F3 med op til 100000000000000000000 års afdragsfrihed",
                "max_interest_only_period",
            ),
        )
        for key, name, value, diagnostic_field in cases:
            institute, kind = ADAPTERS[key]
            with self.subTest(provider=key, field=name):
                data = copy.deepcopy(PAYLOADS[key])
                products = (
                    data
                    if isinstance(data, list)
                    else (
                        data["groups"][0]["entries"]
                        if institute == "TotalKredit"
                        else next(iter(data.values()))
                    )
                )
                products[:] = [products[0]]
                expected, _ = sources.parse(institute, kind, data)
                products.append(dict(products[0], **{name: value}))
                entries, issues = sources.parse(institute, kind, data)
                self.assertEqual(entries, expected)
                issue = next(item for item in issues if item.code == kind + ".product")
                self.assertIn(diagnostic_field + "=", issue.message)
                self.assertIn("PostgreSQL bigint range", issue.message)

    def test_integer_range_validation_covers_rate_period_and_freedom(self):
        for value in (1e300, "1e300", 2**63, str(2**63)):
            for field in ("period", "freedom"):
                with (
                    self.subTest(value=value, field=field),
                    self.assertRaises(sources.SourceError),
                ):
                    sources.rate(
                        "Jyske",
                        **{"period": 3, "freedom": 0, "value": 2.5, field: value},
                    )
        self.assertEqual(sources.number(0, integer=True), 0)
        self.assertEqual(sources.number(2**62, integer=True), 2**62)
        self.assertEqual(sources.number(1e300), 1e300)

    def test_all_invalid_optional_prices_keep_the_product(self):
        for value in (None, "", "unavailable", 0, -1, True, float("nan"), float("inf")):
            with self.subTest(value=value):
                entry = sources.bond("Jyske", 30, value, 97, 0, 0, "DK0009420069")
                self.assertIsNone(entry.spot_price)
                self.assertEqual(entry.offer_price, 97)
                self.assertEqual(entry.coupon_rate, 0)

    def test_unsupported_nordea_offers_are_not_issues(self):
        _, issues = sources.parse("Nordea", "fixed", PAYLOADS["nordea_fixed"])
        self.assertEqual(issues, [])

    def test_products_are_immutable(self):
        entry = sources.rate("Jyske", 3, 0, 2.5)
        with self.assertRaises(FrozenInstanceError):
            entry.spot_rate = 3

    def test_empty_or_broken_envelopes_are_reported(self):
        for institute, kind in ADAPTERS.values():
            for data in ([], {}, None):
                with self.subTest(institute=institute, data=data):
                    entries, issues = sources.parse(institute, kind, data)
                    self.assertEqual(entries, [])
                    self.assertEqual(len(issues), 1)

    def test_input_payloads_are_not_mutated(self):
        for key, (institute, kind) in ADAPTERS.items():
            data = copy.deepcopy(PAYLOADS[key])
            sources.parse(institute, kind, data)
            self.assertEqual(data, PAYLOADS[key])
