import pandas as pd
import sqlalchemy
import os
import logging

DATABASE_PATH = os.environ.get('HEROKU_POSTGRESQL_BRONZE_URL')
if DATABASE_PATH and DATABASE_PATH.startswith("postgres://"):
    # https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
    DATABASE_PATH = DATABASE_PATH.replace("postgres://", "postgresql://", 1)


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    conn = client_factory()

    sql = sqlalchemy.text(sql)
    result = pd.read_sql(sql=sql, con=conn, params=params)
    result.columns = [x.lower() for x in result.columns]

    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])

    logging.info(f'Loaded df with size={len(result)} and columns={result.columns}')
    return result


def client_factory():
    return sqlalchemy.create_engine(DATABASE_PATH)

