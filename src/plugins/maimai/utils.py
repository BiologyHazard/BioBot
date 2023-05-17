import datetime
import time
from random import Random


def get_random_inst(qq: int) -> Random:
    return Random(str(qq) + str(datetime.date.today()))


def strftime(event_time: int) -> str:
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(event_time))
