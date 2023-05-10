import json
import random
from copy import deepcopy
from typing import Any

import aiofiles
import aiohttp
from retrying import retry


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
    brk: int
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
        elif item == 'brk':
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
    charts: Chart
    stats: Stats

    diff: list[int] = []

    def __getattribute__(self, item):
        if item in {'genre', 'artist', 'release_date', 'bpm', 'version'}:
            if item == 'version':
                return self['basic_info']['from']
            return self['basic_info'][item]
        elif item in self:
            return self[item]
        return super().__getattribute__(item)


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

    def random(self) -> Music:
        return random.choice(self)

    def filter(self,
               *,
               level: str | list[str] | None = None,
               ds: float | list[float] | tuple[float, float] | None = None,
               title_search: str | None = None,
               genre: str | list[str] | None = None,
               bpm: float | list[float] | tuple[float, float] | None = None,
               type: str | list[str] | None = None,
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
            if not in_or_equal(music.type, type):
                continue
            if not in_or_equal(music.bpm, bpm):
                continue
            if title_search is not None and title_search.lower() not in music.title.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list


class Aliases(dict[str, Any]):

    id: int
    title: str
    aliases: dict[str, dict]

    def __getattribute__(self, item: str) -> Any:
        if item in self:
            return self[item]
        return super().__getattribute__(item)


class AliasList(dict[str, Aliases]):
    def __init__(self) -> None:
        super().__init__()
        for k, v in self.items():
            self[k] = Aliases(v)

    def by_id(self, id: int): ...

    def by_alias(self, query_alias: str) -> 'AliasList':
        result = AliasList()
        for id, aliases in self.items():
            for alias in aliases.aliases:
                if alias.lower() == query_alias.lower():
                    result[id] = aliases
        return result


total_list = None
aliases_dict = None


@retry(stop_max_attempt_number=3)
async def get_music() -> None:
    global total_list
    async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/music_data') as obj:
        assert obj.status == 200
        music_data = await obj.json()
    async with aiohttp.request("GET", 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as obj:
        assert obj.status == 200
        chart_stats = await obj.json()
    total_list = MusicList(music_data)
    for i in range(len(total_list)):
        total_list[i] = Music(total_list[i])
        total_list[i]['stats'] = chart_stats['charts'][total_list[i].id]
        for j in range(len(total_list[i].charts)):
            total_list[i].charts[j] = Chart(total_list[i].charts[j])
            total_list[i].stats[j] = Stats(total_list[i].stats[j])


async def get_aliases() -> None:
    global aliases_dict
    async with aiofiles.open('data/maimai/aliases.json', 'r', encoding='utf-8') as fp:
        aliases_dict = AliasList(json.loads(await fp.read()))
