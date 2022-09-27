import datetime as dt
import logging


def get_active_date():
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


def is_holiday(date):
    if date.strftime('%Y-%m-%d') in []:
        return True
    return False


def skip_holidays(date):
    if is_holiday(date):
        return skip_holidays(date - dt.timedelta(days=1))
    return date


def get_active_time_range(now=None):
    if now is None:
        now = dt.datetime.utcnow()

    weekday = now.weekday()
    end = dt.datetime(now.year, now.month, now.day, min(now.hour, 15), now.minute - now.minute % 5)
    if weekday == 6:
        end = dt.datetime(now.year, now.month, now.day - 2, 15)
        start = end - dt.timedelta(hours=8)
    elif weekday == 5:
        end = dt.datetime(now.year, now.month, now.day - 1, 15)
        start = end - dt.timedelta(hours=8)
    elif 7 < now.hour < 15:
        if weekday == 0:
            start = end - dt.timedelta(hours=72)
        else:
            start = end - dt.timedelta(hours=24)
    elif now.hour < 7:
        if weekday == 0:
            end = dt.datetime(now.year, now.month, now.day - 3, 15)
        else:
            end = dt.datetime(now.year, now.month, now.day - 1, 15)
        start = end - dt.timedelta(hours=8)
    else:
        start = end - dt.timedelta(hours=8)

    if is_holiday(end):
        return get_active_time_range(dt.datetime(end.year, end.month, end.day-1, 15))

    start = skip_holidays(start)

    return start, end


if __name__ == '__main__':
    # ====================== SUNDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 25, 6, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 25, 12, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 25, 22, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))

    # ====================== SATURDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 24, 6, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 24, 12, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 24, 22, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))

    # ====================== FRIDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 23, 6, 0, 0)) == (dt.datetime(2022, 9, 22, 7), dt.datetime(2022, 9, 22, 15))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 23, 12, 0, 0)) == (dt.datetime(2022, 9, 22, 12), dt.datetime(2022, 9, 23, 12))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 23, 22, 0, 0)) == (dt.datetime(2022, 9, 23, 7), dt.datetime(2022, 9, 23, 15))

    # ====================== WEDNESDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 21, 6, 0, 0)) == (dt.datetime(2022, 9, 20, 7), dt.datetime(2022, 9, 20, 15))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 21, 12, 0, 0)) == (dt.datetime(2022, 9, 20, 12), dt.datetime(2022, 9, 21, 12))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 21, 22, 0, 0)) == (dt.datetime(2022, 9, 21, 7), dt.datetime(2022, 9, 21, 15))

    # ====================== MONDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 19, 6, 0, 0)) == (dt.datetime(2022, 9, 16, 7), dt.datetime(2022, 9, 16, 15))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 19, 12, 0, 0)) == (dt.datetime(2022, 9, 16, 12), dt.datetime(2022, 9, 19, 12))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 19, 22, 0, 0)) == (dt.datetime(2022, 9, 19, 7), dt.datetime(2022, 9, 19, 15))

    # ====================== HOLIDAY TEST ======================
    # morning
    # assert get_active_time_range(dt.datetime(2022, 9, 12, 6, 0, 0)) == (dt.datetime(2022, 9, 8, 7), dt.datetime(2022, 9, 8, 15))
    # # mid-day
    # assert get_active_time_range(dt.datetime(2022, 9, 12, 12, 0, 0)) == (dt.datetime(2022, 9, 8, 12), dt.datetime(2022, 9, 12, 12))
    # # evening
    # assert get_active_time_range(dt.datetime(2022, 9, 12, 22, 0, 0)) == (dt.datetime(2022, 9, 12, 7), dt.datetime(2022, 9, 12, 15))
