import datetime
import json
from typing import Self
from pathlib import Path

from .config import data_path


def strftime(event_time: int) -> str:
    return datetime.datetime.fromtimestamp(event_time).strftime('%H:%M:%S')


def strftimedelta(time0: int, time1: int) -> str:
    delta = datetime.datetime.fromtimestamp(time1) - datetime.datetime.fromtimestamp(time0)
    seconds: int = delta.seconds
    hour, minute, second = seconds // 3600, seconds % 3600 // 60, seconds % 60
    if hour > 0:
        return f'{hour}小时{minute}分钟'
    if minute > 0:
        return f'{minute}分钟'
    return f'{second}秒'


class Tygj:
    def __init__(self, num: int, qqid: int | None, nickname: str | None, card: str | None, role: str | None, time: int) -> None:
        self.num: int = num
        self.qqid: int | None = qqid
        self.nickname: str | None = nickname
        self.card: str | None = card
        self.role: str | None = role
        self.time: int = time

    @classmethod
    def load_from_file(cls, path: Path) -> Self | None:
        if not path.exists():
            return None
        else:
            return cls(**json.loads(data_path.read_text()))

    def save_to_file(self, path: Path) -> Self:
        if not path.parent.exists():
            path.parent.mkdir()
        path.write_text(json.dumps(self.__dict__, ensure_ascii=False, indent=4))
        return self

    @staticmethod
    def in_business_hours(event_time: float) -> bool:
        return 9 <= datetime.datetime.fromtimestamp(event_time).hour < 22
