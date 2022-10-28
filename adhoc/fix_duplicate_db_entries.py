from datetime import datetime

from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler

if __name__ == '__main__':
    spot_prices = postgres_conn.query_db(f"SELECT * FROM spot_prices where timestamp = '2022-10-28 10:30:00'")
    unique = spot_prices.drop_duplicates()
    postgres_conn.client_factory().execute("DELETE from spot_prices where timestamp = '2022-10-28 10:30:00'")
    DatabaseResultHandler(postgres_conn, "spot_prices", datetime.utcnow()).export_result(unique)
