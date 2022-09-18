from datetime import datetime


class ResultHandler:
    def __init__(self, scrape_time: datetime):
        self.scrape_time = scrape_time

    def result_exists(self) -> bool:
        raise NotImplementedError

    def export_result(self, result) -> None:
        raise NotImplementedError
