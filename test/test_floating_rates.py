import tempfile
import unittest
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pandas as pd
from sqlalchemy import create_engine, text

from credit_institute_scraper.scrapers.jyske_scraper import JyskeScraper
from credit_institute_scraper.scrapers.realkredit_danmark_floating_scraper import RealKreditDanmarkFloatingScraper
from credit_institute_scraper.scrapers.total_kredit_floating_scraper import TotalKreditFloatingScraper
from credit_institute_scraper.scrapers.scraper import EmptyScrapeError
from credit_institute_scraper.bond_data.floating_rate_bond_data import FloatingRateBondData
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler


class FloatingRateTests(unittest.TestCase):
    def test_each_scraper_discards_zero_but_keeps_positive_and_negative_rates(self):
        rates = ['0', '0.00', '-0.25', '2.75']
        cases = [
            (JyskeScraper(), {'variabelRenteProdukter': [
                {'fastrenteperiode': 3, 'vaegtetTilbudskursProcent': rate} for rate in rates]}),
            (RealKreditDanmarkFloatingScraper(), [
                {'name': 'FlexLoan_F3_WithInstallment', 'offerrate': rate} for rate in rates]),
            (TotalKreditFloatingScraper(), {'groups': [{'entries': [
                {'name': 'F3 med afdrag', 'innerInterestGrossValue': rate.replace('.', ',') + '%'}
                for rate in rates]}]}),
        ]
        for scraper, payload in cases:
            with self.subTest(scraper=type(scraper).__name__):
                scraper.get_data = Mock(return_value=payload)
                with self.assertLogs(level='WARNING') as logs:
                    bonds = scraper.parse_floating_rate_bonds()
                self.assertEqual([bond.spot_rate for bond in bonds], [-0.25, 2.75])
                self.assertTrue(scraper.missing_observations)
                self.assertTrue(scraper.scrape_success)
                self.assertEqual(len(logs.output), 2)
                self.assertIn(scraper.institute.name, logs.output[0])

    def test_database_writer_filters_zero_rates_even_without_scraper(self):
        with tempfile.TemporaryDirectory() as directory:
            engine = create_engine('sqlite:///' + str(Path(directory) / 'rates.db'))
            module = SimpleNamespace(client_factory=lambda: engine)
            writer = DatabaseResultHandler(module, 'rates', datetime(2026, 9, 12))
            with engine.begin() as connection:
                connection.execute(text('CREATE TABLE rates (timestamp TIMESTAMP, institute TEXT, fixed_rate_period INTEGER, max_interest_only_period TEXT, spot_rate REAL)'))
            frame = pd.DataFrame({'spot_rate': [0, '0.00', -0.25, 2.75], 'institute': ['Jyske'] * 4,
                                  'timestamp': [datetime(2026, 9, 12)] * 4,
                                  'fixed_rate_period': [1, 2, 3, 5], 'max_interest_only_period': [0] * 4})
            with self.assertLogs(level='WARNING'):
                writer.export_result(frame)
            with engine.connect() as connection:
                self.assertEqual(connection.execute(text('SELECT spot_rate FROM rates ORDER BY spot_rate')).scalars().all(), [-0.25, 2.75])
            self.assertEqual(len(frame), 4)
            engine.dispose()

    def test_all_zero_or_empty_scrape_does_not_open_database(self):
        module = SimpleNamespace(client_factory=Mock(side_effect=AssertionError('Should not open database')))
        writer = DatabaseResultHandler(module, 'rates', datetime(2026, 9, 12))
        scraper = RealKreditDanmarkFloatingScraper()
        scraper.get_data = Mock(return_value=[{'name': 'FlexLoan_F5_WithoutInstallment', 'offerrate': '0'}])
        with self.assertLogs(level='WARNING'), self.assertRaises(EmptyScrapeError):
            scraper.parse_floating_rate_bonds()
        writer.export_result(FloatingRateBondData([]).to_data_frame(datetime(2026, 9, 12)))
        with self.assertLogs(level='WARNING'):
            writer.export_result(pd.DataFrame({'spot_rate': [0, 0], 'timestamp': [datetime(2026, 9, 12)] * 2,
                                              'institute': ['Jyske'] * 2, 'fixed_rate_period': [3, 5], 'max_interest_only_period': [0, 0]}))
        module.client_factory.assert_not_called()


if __name__ == '__main__':
    unittest.main()
