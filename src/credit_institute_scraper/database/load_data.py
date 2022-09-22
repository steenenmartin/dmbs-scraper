import datetime as dt
import pandas as pd
from credit_institute_scraper.enums.price_type import PriceType
from typing import Callable


def calculate_open_high_low_close_prices(today: dt.datetime, query_func: Callable) -> pd.DataFrame:
    today_prices = query_func("select * from prices where date(timestamp) = :today", params=locals())
    today_prices.sort_values("timestamp")

    ohlc_prices = pd.DataFrame()
    for isin in set(today_prices["isin"]):
        isin_prices = today_prices.loc[today_prices["isin"] == isin]
        for price_type in PriceType:
            if price_type == PriceType.Open:
                ohlc_price = isin_prices[isin_prices.timestamp == isin_prices.iloc[0].timestamp]
            elif price_type == PriceType.Close:
                ohlc_price = isin_prices[isin_prices.timestamp == isin_prices.iloc[-1].timestamp]
            elif price_type == PriceType.High:
                ohlc_price = isin_prices[isin_prices.spot_price == isin_prices.spot_price.max()].iloc[[0]]
            elif price_type == PriceType.Low:
                ohlc_price = isin_prices[isin_prices.spot_price == isin_prices.spot_price.min()].iloc[[0]]
            elif price_type == PriceType.Average:
                ohlc_price = isin_prices.iloc[[0]]
                ohlc_price = ohlc_price.assign(spot_price=isin_prices.spot_price.mean())
            else:
                raise NotImplementedError

            ohlc_price.insert(len(ohlc_price.columns), "price_type", price_type.name)
            ohlc_prices = pd.concat([ohlc_prices, ohlc_price])

    ohlc_prices = ohlc_prices.assign(timestamp=today)
    return ohlc_prices