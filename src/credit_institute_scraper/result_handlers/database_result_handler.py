from ..database.ingestion import transaction, prepare_observations, write_observations, write_log
from .result_handler import ResultHandler


class DatabaseResultHandler(ResultHandler):
    def __init__(self, database_conn, table_name, *args, **kwargs):
        self._database_conn = database_conn
        self._table_name = table_name
        super().__init__(*args, **kwargs)

    def export_result(self, result_df, if_exists='append'):
        if self.table_name in {'master_data', 'master_data_float'}:
            raise ValueError('Use save_master_data for master tables')
        if if_exists != 'append':
            raise ValueError('Scraping cannot replace or recreate database tables')
        if self.table_name not in {'spot_prices', 'offer_prices', 'closing_prices', 'ohlc_prices', 'rates', 'scrape_logs'}:
            raise ValueError(f'Unsupported ingestion table: {self.table_name}')
        if result_df.empty:
            return
        if self.table_name != 'scrape_logs':
            result_df = prepare_observations(result_df, self.table_name)
            if result_df.empty:
                return
        with transaction(self.database_conn) as connection:
            if self.table_name == 'scrape_logs':
                for row in result_df.to_dict('records'):
                    write_log(connection, row['time'], str(row['error']))
            else:
                write_observations(connection, result_df, self.table_name)

    def result_exists(self):
        # Table is an allowlisted identifier; values are always bound parameters.
        if self.table_name not in {'spot_prices', 'offer_prices', 'closing_prices', 'ohlc_prices', 'rates'}:
            raise ValueError('Unsupported observation table')
        result = self.database_conn.query_db(
            f'SELECT 1 FROM "{self.table_name}" WHERE timestamp=:timestamp LIMIT 1',
            params={'timestamp': self.scrape_time})
        return not result.empty

    @property
    def table_name(self):
        return self._table_name

    @property
    def database_conn(self):
        return self._database_conn
