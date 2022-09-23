import pandas as pd
import sqlite3
import os
import logging

DATABASE_PATH = os.path.abspath(f"{__file__}/../../../../database.db")


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])

    logging.info(f'Loaded df with size={len(result)} and columns={result.columns}')
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)


if __name__ == '__main__':
    import datetime as dt
    date = dt.date(2022, 9, 16)
    df = query_db("select * from prices")
    print(df)