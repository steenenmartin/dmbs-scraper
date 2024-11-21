from datetime import datetime
import sqlalchemy
from credit_institute_scraper.database import postgres_conn
from credit_institute_scraper.result_handlers.database_result_handler import DatabaseResultHandler

if __name__ == '__main__':
    where = "where spot_price = -1"
    print(postgres_conn.query_db("select * from closing_prices " + where).head())
    with postgres_conn.client_factory().connect() as conn:
        result = conn.execute(sqlalchemy.text("DELETE from spot_prices " + where))
        conn.commit()