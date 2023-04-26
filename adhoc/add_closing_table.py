from datetime import datetime

from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler

if __name__ == '__main__':
    closing_prices = postgres_conn.query_db(f"select timestamp, isin, close_price from ohlc_prices")
    closing_prices.rename(columns={"close_price": "spot_price"}, inplace=True)
    DatabaseResultHandler(postgres_conn, 'closing_prices', datetime.utcnow()).export_result(closing_prices, if_exists="replace")
