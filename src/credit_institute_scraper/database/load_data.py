import datetime as dt
import pandas as pd
from typing import Callable


def calculate_open_high_low_close_prices(today: dt.datetime, query_func: Callable) -> pd.DataFrame:
    today_prices = query_func("select * from spot_prices where date(timestamp) = :today", params=locals())
    today_prices.sort_values("timestamp")

    ohlc_prices = pd.DataFrame()
    for isin in set(today_prices["isin"]):
        isin_prices = today_prices.loc[today_prices["isin"] == isin]

        if isin_prices.spot_price.isnull().all():
            continue

        ohlc_price = pd.DataFrame(columns=["timestamp", "isin", "open_price", "high_price", "low_price", "close_price"])
        ohlc_price.loc[0] = [
            today,
            isin,
            isin_prices[isin_prices.timestamp == isin_prices.iloc[0].timestamp].spot_price.iloc[0],
            isin_prices[isin_prices.spot_price == isin_prices.spot_price.max()].spot_price.iloc[0],
            isin_prices[isin_prices.spot_price == isin_prices.spot_price.min()].spot_price.iloc[0],
            isin_prices[isin_prices.timestamp == isin_prices.iloc[-1].timestamp].spot_price.iloc[0]
        ]

        ohlc_prices = pd.concat([ohlc_prices, ohlc_price])

    return ohlc_prices