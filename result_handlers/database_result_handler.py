import pandas as pd
from database import query_db, client_factory
from result_handlers.result_handler import ResultHandler


class DatabaseResultHandler(ResultHandler):
    def export_result(self, result):
        with client_factory() as conn:
            result_df = result.to_pandas_data_frame()
            result_df["time"] = self.scrape_time
            result_df.to_sql(name="prices", con=conn, if_exists='append')

    def result_exists(self):
        result = query_db(f"select * from prices where time = '{self.scrape_time}'")
        return not result.empty

    @property
    def database_path(self):
        return "./database.db"
