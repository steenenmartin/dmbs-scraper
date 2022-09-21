import pandas as pd
import sqlite3
import os
DATABASE_PATH = os.path.abspath(f"{__file__}/../../../../database.db")


def query_db(sql: str, params: dict = None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)


if __name__ == '__main__':
    import datetime as dt
    date = dt.date(2022, 9, 16)
    df = query_db("select * from prices")
    print(df)