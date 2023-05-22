from typing import Iterable, overload
import json
import random
from copy import deepcopy
from typing import Any

import aiofiles
import aiohttp
from retrying import retry
import asyncio


def cross(checker: list[Any], elem: Any | list[Any] | None, diff):
    ret = False
    diff_ret = []
    if not elem or elem is None:
        return True, diff
    if isinstance(elem, list):
        for _j in (range(len(checker)) if diff is None else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if __e in elem:
                diff_ret.append(_j)
                ret = True
    elif isinstance(elem, tuple):
        for _j in (range(len(checker)) if diff is None else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem[0] <= __e <= elem[1]:
                diff_ret.append(_j)
                ret = True
    else:
        for _j in (range(len(checker)) if diff is None else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem == __e:
                return True, [_j]
    return ret, diff_ret


def in_or_equal(checker: Any, elem: Any | list[Any] | None):
    if elem is None:
        return True
    if isinstance(elem, list):
        return checker in elem
    elif isinstance(elem, tuple):
        return elem[0] <= checker <= elem[1]
    else:
        return checker == elem


class Stats:
    def __init__(self, obj) -> None:
        self.cnt: int = obj['cnt']
        self.diff: str = obj['diff']
        self.fit_diff: float = obj['fit_diff']
        self.avg: float = obj['avg']
        self.avg_dx: float = obj['avg_dx']
        self.std_dev: float = obj['std_dev']
        self.dist: list[int] = obj['dist']
        self.fc_dist: list[int] = obj['fc_dist']

    def __repr__(self) -> str:
        return self.__class__.__name__ + '(' + ', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items()) + ')'


class Chart:
    def __init__(self, obj) -> None:
        self.is_dx: bool = len(obj['notes']) == 5
        self.tap: int = obj['notes'][0]
        self.hold: int = obj['notes'][1]
        self.slide: int = obj['notes'][2]
        self.touch: int = obj['notes'][3] if len(obj['notes']) == 5 else 0
        self.break_: int = obj['notes'][-1]
        self.charter: str = obj['charter']

    def __repr__(self) -> str:
        return self.__class__.__name__ + '(' + ', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items()) + ')'


class Music:
    stats: list[Stats]
    aliases: dict[str, dict[str, Any]]

    def __init__(self, obj) -> None:
        if isinstance(obj, Music):
            super().__init__()
            return
        self.id: str = obj['id']
        self.title: str = obj['title']
        self.type: str = obj['type']
        self.ds: list[float] = obj['ds']
        self.level: list[str] = obj['level']
        self.artist: str = obj['basic_info']['artist']
        self.genre: str = obj['basic_info']['genre']
        self.bpm: float = obj['basic_info']['bpm']
        self.release_date: str = obj['basic_info']['release_date']
        self.version: str = obj['basic_info']['from']
        self.charts: list[Chart] = [Chart(chart) for chart in obj['charts']]

        self.diff: list[int] = []

    @property
    def has_remaster(self) -> bool:
        return len(self.level) == 5

    def __repr__(self) -> str:
        return self.__class__.__name__ + '(' + ', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items()) + ')'


class MusicList(list[Music]):
    def __init__(self, obj=None) -> None:
        if obj is None:
            super().__init__()
            return
        super().__init__(Music(music) for music in obj)

    def by_id(self, music_id: str) -> Music | None:
        for music in self:
            if music.id == music_id:
                return music
        return None

    def by_title(self, music_title: str) -> Music | None:
        for music in self:
            if music.title == music_title:
                return music
        return None

    def by_alias(self, music_alias: str) -> 'MusicList':
        '''标题的字串也可以'''
        music_alias = music_alias.strip().lower()
        return MusicList(music for music in self
                         if music_alias in music.title.lower()
                         or any(alias.strip().lower() == music_alias for alias in music.aliases))

    def random(self) -> Music:
        return random.choice(self)

    def filter(self,
               *,
               level: str | list[str] | None = None,
               ds: float | list[float] | tuple[float, float] | None = None,
               title_search: str | None = None,
               genre: str | list[str] | None = None,
               bpm: float | list[float] | tuple[float, float] | None = None,
               type_: str | list[str] | None = None,
               diff: list[int] | None = None,
               ) -> "MusicList":
        new_list = MusicList()
        for music in self:
            diff2: list[int] | None = diff
            music: Music = deepcopy(music)
            ret, diff2 = cross(music.level, level, diff2)
            if not ret:
                continue
            ret, diff2 = cross(music.ds, ds, diff2)
            if not ret:
                continue
            if not in_or_equal(music.genre, genre):
                continue
            if not in_or_equal(music.type, type_):
                continue
            if not in_or_equal(music.bpm, bpm):
                continue
            if title_search is not None and title_search.lower() not in music.title.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list


class Mai:
    music_list: MusicList

    @classmethod
    @retry(stop_max_attempt_number=3)
    async def get_music(cls) -> None:
        async def get_music_data() -> Any:
            async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/music_data') as obj:
                assert obj.status == 200
                return await obj.json()

        async def get_chart_stats() -> Any:
            async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as obj:
                assert obj.status == 200
                return await obj.json()

        music_data, chart_stats = await asyncio.gather(get_music_data(), get_chart_stats())
        # import requests
        # with requests.get('https://www.diving-fish.com/api/maimaidxprober/music_data') as obj:
        #     music_data = obj.json()
        # with requests.get('https://www.diving-fish.com/api/maimaidxprober/chart_stats') as obj:
        #     chart_stats = obj.json()
        cls.music_list = MusicList(music_data)
        for music in cls.music_list:
            music.stats = []
            for stats_dict in chart_stats['charts'][music.id]:
                if stats_dict:
                    music.stats.append(Stats(stats_dict))

    @classmethod
    async def get_aliases(cls) -> None:
        async with aiofiles.open('data/maimai/aliases.json', 'r', encoding='utf-8') as fp:
            obj: dict = json.loads(await fp.read())
        for music in cls.music_list:
            if music.id in obj:
                music.aliases = obj[music.id]['aliases']
            else:
                music.aliases = {}


if __name__ == '__main__':
    asyncio.run(Mai.get_music())
    asyncio.run(Mai.get_aliases())
    print(Mai.music_list[0])
