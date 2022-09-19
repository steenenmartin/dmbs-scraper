import pandas as pd
import sqlite3
DATABASE_PATH = "../../../database.db"


def query_db(sql: str, params: dict = None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)


if __name__ == '__main__':
    import logging
    import credit_institute_scraper
    import datetime as dt
    logging.info("test")
    # df = query_db("select * from prices where to_date(timestamp, 'yyyy-mm-dd') >= :stamp", params={'stamp': dt.datetime(2022, 9, 16)})
    df = query_db("select * from prices where date(timestamp) = :stamp", params={'stamp': dt.date(2022, 9, 16)})

    print(df)
