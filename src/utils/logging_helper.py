import logging
LOGGING_PATH = f'{__file__}\\..\\..\\..\\'


def initiate_logger(logging_level=logging.INFO):
    log_formatter = logging.Formatter("%(asctime)s [%(name)s: %(threadName)s] [%(levelname)s]  %(message)s")
    root_logger = logging.getLogger()

    file_handler = logging.FileHandler(LOGGING_PATH + 'realkreditscraper.log', mode='w', delay=True)
    file_handler.setFormatter(log_formatter)
    root_logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    root_logger.addHandler(console_handler)

    logging.getLogger().setLevel(logging_level)


if __name__ == '__main__':
    initiate_logger()
    logging.info('test_msg')
