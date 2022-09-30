from datetime import datetime
import pandas as pd

from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler

if __name__ == '__main__':
    prices_df = postgres_conn.query_db(f"SELECT * FROM prices")
    master_data = prices_df[["isin", "institute", "years_to_maturity", "max_interest_only_period", "coupon_rate"]].drop_duplicates()
    master_data = master_data.drop(master_data[(master_data["institute"] == "Nordea") & (master_data["years_to_maturity"] == 15)].index)
    DatabaseResultHandler(postgres_conn, 'master_data', datetime.utcnow()).export_result(master_data)

    spot_prices_df = prices_df
    spot_prices_df = spot_prices_df.drop(spot_prices_df[(spot_prices_df["institute"] == "Nordea") & (spot_prices_df["years_to_maturity"] == 15)].index)
    spot_prices_df = spot_prices_df[["timestamp", "isin", "spot_price"]]
    DatabaseResultHandler(postgres_conn, 'spot_prices', datetime.utcnow()).export_result(spot_prices_df)

    ohlc_prices = postgres_conn.query_db(f"SELECT * FROM ohlc_prices")
    ohlc_prices = ohlc_prices.drop(ohlc_prices[(ohlc_prices["institute"] == "Nordea") & (ohlc_prices["years_to_maturity"] == 15)].index)
    grouped_ohld_prices = ohlc_prices.groupby(["timestamp", "isin"])
    new_ohlc_cols = ["timestamp", "isin", "open_price", "high_price", "low_price", "close_price"]
    new_ohlc_prices = pd.DataFrame(columns=new_ohlc_cols)
    for name, group in grouped_ohld_prices:
        new_ohlc_price = pd.DataFrame(columns=new_ohlc_cols)
        new_ohlc_price.loc[0] = [
             group.iloc[0]["timestamp"],
             group.iloc[0]["isin"],
             group.loc[group["price_type"] == "Open"].spot_price.iloc[0],
             group.loc[group["price_type"] == "High"].spot_price.iloc[0],
             group.loc[group["price_type"] == "Low"].spot_price.iloc[0],
             group.loc[group["price_type"] == "Close"].spot_price.iloc[0]
        ]
        new_ohlc_prices = pd.concat([new_ohlc_prices, new_ohlc_price])
    DatabaseResultHandler(postgres_conn, 'ohlc_pricez', datetime.utcnow()).export_result(new_ohlc_prices)




