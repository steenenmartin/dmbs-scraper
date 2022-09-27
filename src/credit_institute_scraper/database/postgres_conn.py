import pandas as pd
import sqlalchemy
import os
import logging
import json
from ..utils.server_helper import is_heroku_server


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    conn = client_factory()

    sql = sqlalchemy.text(sql)
    result = pd.read_sql(sql=sql, con=conn, params=params)
    conn.dispose()
    result.columns = [x.lower() for x in result.columns]

    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])

    logging.info(f'Loaded df with size={len(result)} and columns={result.columns}')
    return result


def client_factory():
    return sqlalchemy.create_engine(connection_string())


def connection_string():
    if is_heroku_server():
        database_path = os.environ.get('HEROKU_POSTGRESQL_BRONZE_URL')
        if database_path and database_path.startswith("postgres://"):
            # https://stackoverflow.com/questions/62688256/sqlalchemy-exc-nosuchmoduleerror-cant-load-plugin-sqlalchemy-dialectspostgre
            database_path = database_path.replace("postgres://", "postgresql://", 1)
    else:
        with open('credentials.json') as fo:
            crd = json.load(fo)
        database_path = f'postgresql://{crd["user"]}:{crd["password"]}@{crd["host"]}:{crd["port"]}/{crd["database"]}'
    return database_path


def execute_statements(statements: list):
    engine = client_factory()
    conn = engine.connect()
    trans = conn.begin()
    try:
        for statement in statements:
            conn.execute(statement)
        trans.commit()
    except Exception as e:
        logging.error(e)
        trans.rollback()
