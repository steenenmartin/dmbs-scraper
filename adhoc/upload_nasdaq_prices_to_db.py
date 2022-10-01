import pandas as pd
import datetime
from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler

if __name__ == "__main__":
    isins = postgres_conn.query_db(f"SELECT * FROM master_data")['isin'].unique()

    postgres_conn.client_factory().execute(f"DELETE FROM ohlc_pricez where timestamp < '2022-09-23 00:00:00'")

    i = 0
    df_out = pd.DataFrame()
    result_handler = DatabaseResultHandler(postgres_conn, 'ohlc_pricez', datetime.datetime.utcnow())

    for isin in isins:
        i += 1
        print(i)
        nasdaq_df = pd.read_csv(fr"C:\Users\MartinSteenAndersenE\Downloads\Kurser\{isin}.csv", sep=";", skiprows=1)
        db_df = postgres_conn.query_db(f"SELECT * FROM ohlc_pricez where isin = '{isin}' limit 1")

        prev_close = None

        for index, row in nasdaq_df.iterrows():
            date = pd.to_datetime(row['Date'])

            if date >= datetime.datetime(2022, 9, 23):
                continue

            high_price = row['Highprice']
            low_price = row['Lowprice']
            closing_price = row['Closingprice']

            if pd.isnull(high_price) and pd.isnull(low_price) and pd.isnull(closing_price):
                continue

            if prev_close is not None:
                db_df['timestamp'] = date
                db_df['high_price'] = high_price
                db_df['low_price'] = low_price
                db_df['open_price'] = prev_close if prev_close < high_price else high_price
                db_df['close_price'] = closing_price

                df_out = pd.concat([df_out, db_df])

            prev_close = closing_price

    result_handler.export_result(df_out)

