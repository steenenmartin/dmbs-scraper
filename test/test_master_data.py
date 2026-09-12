import logging
import sqlite3
import unittest

import pandas as pd
from sqlalchemy import create_engine, text

from credit_institute_scraper.database.master_data import normalize_master_data, insert_master_data
from credit_institute_scraper.bond_data.fixed_rate_bond_data import FixedRateBondData
from credit_institute_scraper.bond_data.floating_rate_bond_data import FloatingRateBondData
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler


def fixed(**changes):
    return dict(isin='DK0002066521', institute='Nordea', years_to_maturity=20,
                max_interest_only_period=0, coupon_rate=3.5) | changes


def floating(**changes):
    return dict(institute='Jyske', fixed_rate_period=3, max_interest_only_period=0) | changes


class MasterDataTests(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine('sqlite://')
        with self.engine.begin() as conn:
            conn.execute(text('CREATE TABLE master_data (isin TEXT NOT NULL, institute TEXT, years_to_maturity INTEGER, max_interest_only_period INTEGER, coupon_rate REAL, UNIQUE(isin, years_to_maturity, max_interest_only_period))'))
            conn.execute(text("CREATE UNIQUE INDEX master_data_jyske_isin_key ON master_data(isin) WHERE institute='Jyske'"))
            conn.execute(text('CREATE TABLE master_data_float (institute TEXT NOT NULL, fixed_rate_period INTEGER NOT NULL, max_interest_only_period INTEGER NOT NULL, UNIQUE(institute, fixed_rate_period, max_interest_only_period))'))

    def tearDown(self):
        self.engine.dispose()

    def write(self, rows, table='master_data'):
        with self.engine.begin() as conn:
            return insert_master_data(conn, pd.DataFrame(rows), table)

    def records(self, table='master_data'):
        with self.engine.connect() as conn:
            return [dict(row) for row in conn.execute(text(f'SELECT * FROM {table}')).mappings()]

    def test_old_mixed_types_reproduce_floating_duplicates(self):
        old = pd.DataFrame([floating(max_interest_only_period='0')])
        scrape = pd.DataFrame([floating(max_interest_only_period=0)])
        self.assertEqual(len(pd.concat([old, scrape]).drop_duplicates()), 2)
        self.assertEqual(self.write([*old.to_dict('records'), *scrape.to_dict('records')], 'master_data_float'), 1)
        self.assertEqual(self.write([floating(max_interest_only_period='0.0')], 'master_data_float'), 0)
        self.assertEqual(len(self.records('master_data_float')), 1)

    def test_nordea_product_variants_remain_independently_filterable(self):
        for rows in ([fixed(years_to_maturity=15), fixed()], [fixed(), fixed(years_to_maturity=15)]):
            result = normalize_master_data(pd.DataFrame(rows), 'master_data')
            self.assertEqual(sorted(result['years_to_maturity'].tolist()), [15, 20])

    def test_jyske_product_variants_choose_maximum_interest_only_years(self):
        for years in (10, 30):
            a = fixed(isin='DK0009420143', institute='Jyske', years_to_maturity=30, coupon_rate=4)
            result = normalize_master_data(pd.DataFrame([a, a | {'max_interest_only_period': years}]), 'master_data')
            self.assertEqual(result.iloc[0].max_interest_only_period, years)

    def test_repeated_scrapes_and_partial_scrapes_keep_one_record(self):
        self.assertEqual(self.write([fixed(), fixed(years_to_maturity=15)]), 2)
        self.assertEqual(self.write([fixed()]), 0)
        self.assertEqual(self.write([fixed(years_to_maturity=15)]), 0)
        self.assertEqual(len(self.records()), 2)

    def test_jyske_manual_corrections_survive_scraping(self):
        jyske = fixed(isin='DK0009420143', institute='Jyske', years_to_maturity=30, coupon_rate=4)
        self.write([jyske])
        with self.engine.begin() as conn:
            conn.execute(text("UPDATE master_data SET max_interest_only_period=10"))
        with self.assertLogs(level=logging.WARNING) as logs:
            self.assertEqual(self.write([jyske]), 0)
        self.assertIn('Preserving existing', '\n'.join(logs.output))
        self.assertEqual(len(self.records()), 1)
        self.assertEqual(self.records()[0]['max_interest_only_period'], 10)

    def test_unexpected_coupon_or_institute_conflict_is_not_guessed(self):
        for other in (fixed(coupon_rate=9), fixed(institute='Jyske')):
            with self.assertLogs(level=logging.WARNING):
                self.assertEqual(self.write([fixed(), other]), 0)
        self.assertEqual(self.records(), [])

    def test_identity_conflicts_across_scrapes_cannot_enter_as_new_products(self):
        self.write([fixed()])
        for other in (fixed(years_to_maturity=15, coupon_rate=9),
                      fixed(years_to_maturity=15, institute='Jyske')):
            with self.assertLogs(level=logging.WARNING) as logs:
                self.assertEqual(self.write([other]), 0)
            self.assertIn('manual review', '\n'.join(logs.output))
        self.assertEqual(self.records(), [fixed()])
        self.assertEqual(self.write([fixed(years_to_maturity=15)]), 1)

    def test_jyske_conflicting_observations_are_logged(self):
        jyske = fixed(isin='DK0009420143', institute='Jyske', years_to_maturity=30, coupon_rate=4)
        with self.assertLogs(level=logging.WARNING) as logs:
            self.assertEqual(self.write([jyske, jyske | {'max_interest_only_period': 10}]), 1)
        self.assertIn('DK0009420143', '\n'.join(logs.output))
        self.assertIn('Conflicting Jyske', '\n'.join(logs.output))
        self.assertEqual(self.records()[0]['max_interest_only_period'], 10)

    def test_missing_values_do_not_delete_existing_data(self):
        self.write([fixed()])
        self.assertEqual(self.write([]), 0)
        with self.assertLogs(level=logging.WARNING):
            self.assertEqual(self.write([fixed(coupon_rate=float('nan')), fixed(isin=None)]), 0)
        self.assertEqual(self.records(), [fixed()])

    def test_floating_interest_only_options_remain_distinct(self):
        self.assertEqual(self.write([floating(), floating(max_interest_only_period=10), floating(max_interest_only_period=30)], 'master_data_float'), 3)
        self.assertEqual(len(self.records('master_data_float')), 3)

    def test_database_constraint_rejects_duplicate_even_outside_writer(self):
        self.write([fixed()])
        with self.assertRaises(Exception):
            with self.engine.begin() as conn:
                conn.execute(text('INSERT INTO master_data SELECT * FROM master_data'))
        self.assertEqual(len(self.records()), 1)

    def test_missing_migration_fails_without_replacing_table(self):
        connection = sqlite3.connect(':memory:')
        connection.execute('CREATE TABLE master_data (isin TEXT, institute TEXT, years_to_maturity INTEGER, max_interest_only_period INTEGER, coupon_rate REAL)')
        with self.assertRaises(sqlite3.OperationalError):
            insert_master_data(connection, pd.DataFrame([fixed()]), 'master_data')
        self.assertEqual(connection.execute('SELECT count(*) FROM master_data').fetchone()[0], 0)
        connection.close()

    def test_generic_result_handler_cannot_replace_or_append_master_tables(self):
        for table in ('master_data', 'master_data_float'):
            for mode in ('replace', 'append'):
                handler = DatabaseResultHandler(None, table, None)
                with self.assertRaisesRegex(ValueError, 'save_master_data'):
                    handler.export_result(pd.DataFrame([fixed()]), if_exists=mode)

    def test_empty_scraper_collections_have_master_columns(self):
        self.assertIn('isin', FixedRateBondData([]).to_master_data_frame().columns)
        self.assertIn('fixed_rate_period', FloatingRateBondData([]).to_master_data_frame().columns)


if __name__ == '__main__':
    unittest.main()
