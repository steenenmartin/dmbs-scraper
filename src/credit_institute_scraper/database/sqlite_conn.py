import pandas as pd
import sqlite3
import os
DATABASE_PATH = os.path.abspath(f"{__file__}/../../../../database.db")
print(DATABASE_PATH)


def query_db(sql: str, params: dict = None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)
