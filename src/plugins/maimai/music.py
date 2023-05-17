import json
import random
from copy import deepcopy
from typing import Any

import aiofiles
import aiohttp
from retrying import retry
import asyncio


def get_cover_len4_id(mid) -> str:
    mid = int(mid)
    if mid > 10000:
        mid -= 10000
    return f'{mid:04d}'


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


class Stats(dict):
    cnt: int
    diff: str
    fit_diff: float
    avg: float
    avg_dx: float
    std_dev: float
    dist: list[int]
    fc_dist: list[int]

    def __getattribute__(self, item):
        try:
            if item in self:
                return self[item]
            return super().__getattribute__(item)
        except KeyError:
            return 'Unknown'


class Chart(dict):
    tap: int
    slide: int
    hold: int
    touch: int
    break_: int
    charter: str

    def __getattribute__(self, item):
        if item == 'tap':
            return self['notes'][0]
        elif item == 'hold':
            return self['notes'][1]
        elif item == 'slide':
            return self['notes'][2]
        elif item == 'touch':
            return self['notes'][3] if len(self['notes']) == 5 else 0
        elif item == 'break_':
            return self['notes'][-1]
        elif item == 'charter':
            return self['charter']
        return super().__getattribute__(item)


class Music(dict):
    id: str
    title: str
    type: str
    ds: list[float]
    level: list[str]
    artist: str
    genre: str
    bpm: float
    release_date: str
    version: str
    charts: list[Chart]
    stats: Stats
    aliases: dict[str, dict[str, Any]]

    diff: list[int] = []

    def __getattribute__(self, __name: str) -> Any:
        try:
            return super().__getattribute__(__name)
        except AttributeError:
            if __name in {'genre', 'artist', 'release_date', 'bpm', 'version'}:
                if __name == 'version':
                    return self['basic_info']['from']
                return self['basic_info'][__name]
            elif __name in self:
                return self[__name]
            raise


class MusicList(list[Music]):
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
        for i in range(len(cls.music_list)):
            cls.music_list[i] = Music(cls.music_list[i])
            cls.music_list[i]['stats'] = chart_stats['charts'][cls.music_list[i].id]
            for j in range(len(cls.music_list[i].charts)):
                cls.music_list[i].charts[j] = Chart(cls.music_list[i].charts[j])
                cls.music_list[i].stats[j] = Stats(cls.music_list[i].stats[j])

    @classmethod
    async def get_aliases(cls) -> None:
        async with aiofiles.open('data/maimai/aliases.json', 'r', encoding='utf-8') as fp:
            obj: dict = json.loads(await fp.read())
        for music in cls.music_list:
            if music.id in obj:
                music.aliases = obj[music.id]['aliases']
            else:
                music.aliases = {}
