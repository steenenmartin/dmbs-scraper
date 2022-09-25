import datetime as dt
from .server_helper import is_heroku_server


def get_active_date():
    if not is_heroku_server():
        return dt.date(2022, 9, 21)

    date = dt.date.today()
    weekday = dt.date.today().weekday()
    if weekday == 6:
        date -= dt.timedelta(days=2)
    elif weekday == 5:
        date -= dt.timedelta(days=1)
    elif dt.datetime.now().hour < 7:
        if weekday == 0:
            date -= dt.timedelta(days=3)
        else:
            date -= dt.timedelta(days=1)

    return date
