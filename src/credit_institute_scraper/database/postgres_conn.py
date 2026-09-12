import pandas as pd
import sqlalchemy
import logging
import json
import os


def query_db(sql: str, params: dict = None, cast_date_col=None) -> pd.DataFrame:
    conn = client_factory()

    sql = sqlalchemy.text(sql)
    try:
        result = pd.read_sql(sql=sql, con=conn, params=params)
    finally:
        conn.dispose()
    result.columns = [x.lower() for x in result.columns]

    if cast_date_col is not None:
        result[cast_date_col] = pd.to_datetime(result[cast_date_col])

    logging.info(f'Loaded df with size={len(result)} and columns={result.columns}')
    return result


def client_factory():
    return sqlalchemy.create_engine(connection_string(), pool_pre_ping=True,
                                    connect_args={'connect_timeout': 10, 'options': '-c statement_timeout=30000'})


def connection_string():
    database_url = next((os.environ.get(key) for key in (
        'DATABASE_URL', 'HEROKU_POSTGRESQL_BRONZE_URL',
        'HEROKU_POSTGRESQL_COBALT_URL', 'HEROKU_POSTGRESQL_CRIMSON_URL'
    ) if os.environ.get(key)), None)
    if database_url:
        return database_url.replace('postgres://', 'postgresql://', 1)

    with open(os.path.join(os.path.dirname(__file__), 'credentials.json')) as fo:
        crd = json.load(fo)
    ssl_mode = os.environ.get('DATABASE_SSL', crd.get('ssl'))
    return sqlalchemy.engine.URL.create(
        'postgresql', username=crd['user'], password=crd['password'],
        host=crd['host'], port=int(crd['port']), database=crd['database'],
        query={'sslmode': ssl_mode} if ssl_mode else {},
    )


def execute_statements(statements: list):
    engine = client_factory()
    try:
        with engine.begin() as conn:
            for statement in statements:
                conn.execute(sqlalchemy.text(statement) if isinstance(statement, str) else statement)
    finally:
        engine.dispose()
