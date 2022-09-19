import pandas as pd
import sqlite3
DATABASE_PATH = "../../../database.db"


def query_db(sql: str) -> pd.DataFrame:
    with client_factory() as conn:
        result = pd.read_sql(sql=sql, con=conn)
    return result


def client_factory():
    return sqlite3.connect(DATABASE_PATH)


if __name__ == '__main__':
    import logging
    import src
    logging.info("test")
    df = query_db("select * from prices")

    print(df)
