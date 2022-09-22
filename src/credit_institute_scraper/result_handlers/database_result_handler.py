import pandas as pd
import logging
from ..result_handlers.result_handler import ResultHandler


class DatabaseResultHandler(ResultHandler):
    def __init__(self, database_conn, table_name, *args, **kwargs):
        self._database_conn = database_conn
        self._table_name = table_name
        super().__init__(*args,  **kwargs)

    def export_result(self, result_df: pd.DataFrame) -> None:
        conn = self.database_conn.client_factory()
        result_df.to_sql(name=self.table_name, con=conn, if_exists='append', index=False)
        logging.info(f'Wrote df with size={len(result_df)} to {conn}')

    def result_exists(self) -> bool:
        result = self.database_conn.query_db(f"select * from {self.table_name} where timestamp = '{self.scrape_time}'")
        return not result.empty

    @property
    def database_path(self):
        return "./database.db"

    @property
    def table_name(self):
        return self._table_name

    @property
    def database_conn(self):
        return self._database_conn

