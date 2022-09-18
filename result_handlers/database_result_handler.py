import sqlite3
import pandas as pd
from result_handlers.result_handler import ResultHandler


class DatabaseResultHandler(ResultHandler):
    def export_result(self, result):
        with sqlite3.connect(self.database_path) as conn:
            result_df = result.to_pandas_data_frame()
            result_df["time"] = self.scrape_time
            result_df.to_sql(name="prices", con=conn, if_exists='append')

    def result_exists(self):
        with sqlite3.connect(self.database_path) as conn:
            result = pd.read_sql_query(f"select * from prices where time = '{self.scrape_time}'", conn)

        return not result.empty

    @property
    def database_path(self):
        return "./database.db"
