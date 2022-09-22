import pandas as pd
from sqlalchemy import create_engine
import os

DATABASE_PATH = os.environ.get('DATABASE_URL')


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])
    return result


def client_factory():
    return create_engine(DATABASE_PATH)

