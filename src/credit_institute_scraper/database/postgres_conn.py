import pandas as pd
import psycopg2
import os

DATABASE_PATH = os.environ.get('DATABASE_URL')


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])
    return result


def client_factory():
    return psycopg2.connect(DATABASE_PATH, sslmode='require')

