import os
from ..bond_data.fixed_rate_bond_data import FixedRateBondData
from ..result_handlers.result_handler import ResultHandler


class CsvResultHandler(ResultHandler):
    def result_exists(self) -> bool:
        return os.path.exists(self.csv_path)

    def export_result(self, result: FixedRateBondData) -> None:
        if not os.path.exists(self.day_path):
            os.makedirs(self.day_path)

        result.to_pandas_data_frame().to_csv(self.csv_path, index=False)

    @property
    def csv_path(self) -> str:
        return f"{self.day_path}/{self.scrape_time.strftime('%Y%m%d%H%M')}.csv"

    @property
    def day_path(self) -> str:
        return f"./Kurser/{self.scrape_time.strftime('%Y%m%d')}"
