from datetime import datetime


def print_time_prefixed(s: str):
    print(str(datetime.today()) + "    " + s)
