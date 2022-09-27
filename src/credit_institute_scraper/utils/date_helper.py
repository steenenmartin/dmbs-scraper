import datetime as dt
from .server_helper import is_heroku_server
import logging


def get_active_date():
    if not is_heroku_server():
        return dt.date(2022, 9, 21)

    date = dt.date.today()
    weekday = dt.date.today().weekday()
    reduce_days = 0
    if weekday == 6:
        reduce_days = 2
    elif weekday == 5:
        reduce_days = 1
    elif dt.datetime.utcnow().hour < 7:
        if weekday == 0:
            reduce_days = 3
        else:
            reduce_days = 1

    logging.info(f'Date: {date.isoformat()}, reduced days: {reduce_days}, timestamp: {dt.datetime.utcnow().isoformat()}')
    date -= dt.timedelta(days=reduce_days)

    return date
