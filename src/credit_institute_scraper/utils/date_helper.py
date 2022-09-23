import datetime as dt
from .server_helper import is_heroku_server


def get_active_date():
    if not is_heroku_server():
        return dt.date(2022, 9, 21)

    date = dt.date.today()
    weekday = dt.date.today().weekday()
    if weekday == 6 or dt.datetime.now().hour < 7:
        if weekday == 1:
            date -= dt.timedelta(days=3)
        else:
            date -= dt.timedelta(days=1)
    elif weekday == 7:
        date -= dt.timedelta(days=2)
    return date
