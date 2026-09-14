import logging


def initiate_logger(logging_level=logging.INFO):
    # Stream to Heroku's log collector (or the local terminal). Idempotent and
    # no overwritten log file, Windows-specific path, or import-time handlers.
    logging.basicConfig(level=logging_level,
                        format='%(asctime)s %(levelname)s %(name)s: %(message)s')
