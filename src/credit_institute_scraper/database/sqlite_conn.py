import pandas as pd
import sqlite3
import os
from datetime import datetime
from ..enums.price_type import PriceType

DATABASE_PATH = os.path.abspath(f"{__file__}/../../../../database.db")


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)


def calculate_open_high_low_close_prices(today: datetime) -> pd.DataFrame:
    eod = datetime(today.year, today.month, today.day, 23, 59, 59)
    today_prices = query_db("select * from prices where :stamp1 <= datetime(timestamp) and datetime(timestamp) <= :stamp2", params={'stamp1': today, 'stamp2': eod})
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


if __name__ == '__main__':
    import datetime as dt
    date = dt.date(2022, 9, 16)
    df = query_db("select * from prices")
    print(df)