import datetime as dt
import pandas as pd

from .ingestion import prepare_observations


def calculate_open_high_low_close_prices(today, query_func):
    prices = query_func(
        'SELECT timestamp, isin, spot_price FROM spot_prices WHERE timestamp >= :start AND timestamp < :end ORDER BY timestamp',
        params={'start': today, 'end': today + dt.timedelta(days=1)})
    prices = prepare_observations(prices, 'spot_prices').sort_values('timestamp', kind='stable')
    columns = ['timestamp', 'isin', 'open_price', 'high_price', 'low_price', 'close_price']
    if prices.empty:
        return pd.DataFrame(columns=columns)
    result = prices.groupby('isin', sort=True)['spot_price'].agg(
        open_price='first', high_price='max', low_price='min', close_price='last').reset_index()
    result.insert(0, 'timestamp', today)
    return result[columns]
