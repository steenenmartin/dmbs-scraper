import datetime as dt
import pytz
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
    return date.date() in [
        dt.date(2024, 12, 26),
        dt.date(2024, 12, 31),
        dt.date(2025, 1, 1),
        dt.date(2025, 4, 17),
        dt.date(2025, 4, 18),
        dt.date(2025, 4, 21),
        dt.date(2025, 5, 29),
        dt.date(2025, 5, 30),
        dt.date(2025, 6, 5),
        dt.date(2025, 6, 9),
        dt.date(2025, 12, 24),
        dt.date(2025, 12, 25),
        dt.date(2025, 12, 26),
        dt.date(2025, 12, 31),
    ]

def skip_holidays(date):
    if is_holiday(date):
        return skip_holidays(date - dt.timedelta(days=1))
    return date


def get_active_time_range(now=None, force_9_17=False):
    if now is not None:
        if now.tzinfo is None:
            raise ValueError(f"Expected now.tzinfo not None.")
    else:
        now = pytz.utc.localize(dt.datetime.utcnow())

    tz_cph = pytz.timezone("Europe/Copenhagen")
    now = now.astimezone(tz_cph)

    weekday = now.weekday()
    end = dt.datetime(now.year, now.month, now.day, min(now.hour, 17), now.minute - now.minute % 5)
    if weekday == 6:
        end = dt.datetime(now.year, now.month, now.day, 17) - dt.timedelta(days=2)
        start = end - dt.timedelta(hours=8)
    elif weekday == 5:
        end = dt.datetime(now.year, now.month, now.day, 17) - dt.timedelta(days=1)
        start = end - dt.timedelta(hours=8)
    elif 9 < now.hour < 17:
        if weekday == 0:
            start = end - dt.timedelta(hours=72)
        else:
            start = end - dt.timedelta(hours=24)
    elif now.hour < 9:
        if weekday == 0:
            end = dt.datetime(now.year, now.month, now.day, 17) - dt.timedelta(days=3)
        else:
            end = dt.datetime(now.year, now.month, now.day, 17) - dt.timedelta(days=1)
        start = end - dt.timedelta(hours=8)
    else:
        start = end - dt.timedelta(hours=8)

    if is_holiday(end):
        return get_active_time_range(dt.datetime(end.year, end.month, end.day, 17, tzinfo=tz_cph) - dt.timedelta(days=1))

    start = skip_holidays(start)

    if force_9_17:
        start, end = dt.datetime(end.year, end.month, end.day, 9), dt.datetime(end.year, end.month, end.day, 17)

    start = tz_cph.localize(start)
    end = tz_cph.localize(end)

    return start.astimezone(pytz.utc), end.astimezone(pytz.utc)


if __name__ == '__main__':
    utc = pytz.utc
    # ====================== SUNDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 25, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 25, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 25, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))

    # ====================== SATURDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 24, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 24, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 24, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))

    # ====================== FRIDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 23, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 22, 7, tzinfo=utc), dt.datetime(2022, 9, 22, 15, tzinfo=utc))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 23, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 22, 12, tzinfo=utc), dt.datetime(2022, 9, 23, 12, tzinfo=utc))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 23, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 23, 7, tzinfo=utc), dt.datetime(2022, 9, 23, 15, tzinfo=utc))

    # ====================== WEDNESDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 21, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 20, 7, tzinfo=utc), dt.datetime(2022, 9, 20, 15, tzinfo=utc))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 21, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 20, 12, tzinfo=utc), dt.datetime(2022, 9, 21, 12, tzinfo=utc))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 21, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 21, 7, tzinfo=utc), dt.datetime(2022, 9, 21, 15, tzinfo=utc))

    # ====================== MONDAY ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 9, 19, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 16, 7, tzinfo=utc), dt.datetime(2022, 9, 16, 15, tzinfo=utc))
    # mid-day
    assert get_active_time_range(dt.datetime(2022, 9, 19, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 16, 12, tzinfo=utc), dt.datetime(2022, 9, 19, 12, tzinfo=utc))
    # evening
    assert get_active_time_range(dt.datetime(2022, 9, 19, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 9, 19, 7, tzinfo=utc), dt.datetime(2022, 9, 19, 15, tzinfo=utc))

    # ====================== HOLIDAY TEST ======================
    # morning
    assert get_active_time_range(dt.datetime(2022, 12, 26, 6, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 12, 23, 8, tzinfo=utc), dt.datetime(2022, 12, 23, 16, tzinfo=utc))
    # # mid-day
    assert get_active_time_range(dt.datetime(2022, 12, 26, 12, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 12, 23, 8, tzinfo=utc), dt.datetime(2022, 12, 23, 16, tzinfo=utc))
    # # evening
    assert get_active_time_range(dt.datetime(2022, 12, 26, 22, 0, 0, tzinfo=utc)) == (dt.datetime(2022, 12, 23, 8, tzinfo=utc), dt.datetime(2022, 12, 23, 16, tzinfo=utc))
