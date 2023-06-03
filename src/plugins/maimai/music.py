import asyncio
import json
import random
import copy
from typing import Any, overload, Literal

import aiofiles
import aiohttp
from retrying import retry

from .config import plugin_config
from .consts import GENRE_HAN, VERSION_HAN


class Stats:
    def __init__(self, obj) -> None:
        self.cnt: int = int(obj['cnt'])
        self.diff: str = obj['diff']
        self.fit_diff: float = obj['fit_diff']
        self.avg: float = obj['avg']
        self.avg_dx: float = obj['avg_dx']
        self.std_dev: float = obj['std_dev']
        self.dist: list[int] = obj['dist']
        self.fc_dist: list[int] = obj['fc_dist']

    def __repr__(self) -> str:
        return f'''{self.__class__.__name__}({', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items())})'''


class Chart:
    stats: Stats

    def __init__(self, obj) -> None:
        self.is_dx: bool = len(obj['notes']) == 5
        self.tap: int = obj['notes'][0]
        self.hold: int = obj['notes'][1]
        self.slide: int = obj['notes'][2]
        self.touch: int = obj['notes'][3] if self.is_dx else 0
        self.break_: int = obj['notes'][-1]
        self.notes: int = sum(obj['notes'])
        self.charter: str = obj['charter']

    def __repr__(self) -> str:
        return f'''{self.__class__.__name__}({', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items())})'''


class Music:
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
        self.diff_num: int = len(self.level)
        self.has_remaster: bool = (self.diff_num == 5)
        self.artist: str = obj['basic_info']['artist']
        self.genre: str = obj['basic_info']['genre']
        self.genre_han: str = GENRE_HAN[self.genre]
        self.bpm: float = obj['basic_info']['bpm']
        self.release_date: str = obj['basic_info']['release_date']
        self.version: str = obj['basic_info']['from']
        self.version_han: str = VERSION_HAN[self.version]
        self.charts: list[Chart] = [Chart(chart) for chart in obj['charts']]

        self.diff: list[int] = list(range(self.diff_num))

    def __repr__(self) -> str:
        return f'''{self.__class__.__name__}({', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items())})'''


def _cross(checker: list[Any], elem: Any | tuple[Any, Any] | list[Any] | None, diff: list[int]) -> tuple[bool, list[int]]:
    ret = False
    diff_ret: list[int] = []
    if elem is None:
        return True, diff
    if isinstance(elem, list):
        for _j in diff:
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if __e in elem:
                diff_ret.append(_j)
                ret = True
    elif isinstance(elem, tuple):
        for _j in diff:
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem[0] <= __e <= elem[1]:
                diff_ret.append(_j)
                ret = True
    else:
        for _j in diff:
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem == __e:
                return True, [_j]
    return ret, diff_ret


def _in_or_equal(checker: Any, elem: Any | tuple[Any, Any] | list[Any] | None) -> bool:
    if elem is None:
        return True
    if isinstance(elem, list):
        return checker in elem
    elif isinstance(elem, tuple):
        return elem[0] <= checker <= elem[1]
    else:
        return checker == elem


def _search_charts(checker: list[Chart], elem: str | None, diff: list[int]) -> tuple[bool, list[int]]:
    ret = False
    diff_ret: list[int] = []
    if elem is None:
        return True, diff
    for _j in diff:
        if elem.lower() in checker[_j].charter.lower():
            diff_ret.append(_j)
            ret = True
    return ret, diff_ret


class MusicList(list[Music]):
    @classmethod
    def from_json(cls, obj) -> 'MusicList':
        return cls(Music(music) for music in obj)

    @overload
    def by_id(self, music_id: str, strict: Literal[True] = ...) -> Music: ...

    @overload
    def by_id(self, music_id: str, strict: Literal[False] = ...) -> Music | None: ...

    def by_id(self, music_id: str, strict: bool = False) -> Music | None:
        for music in self:
            if music.id == music_id:
                return music
        if strict:
            raise ValueError(f'Music of id{music_id} not found.')
        return None

    # def by_title(self, music_title: str) -> Music | None:
    #     for music in self:
    #         if music.title == music_title:
    #             return music
    #     return None

    def by_alias(self, music_alias: str) -> 'MusicList':
        '''标题的字串也可以'''
        music_alias = music_alias.strip().lower()
        return MusicList(music for music in self
                         if music_alias in music.title.lower()
                         or any(alias.strip().lower() == music_alias for alias in music.aliases))

    def by_name(self, name: str) -> 'MusicList':
        if name.isdigit() and (music := Mai.music_list.by_id(name)) is not None:
            return MusicList([music])
        else:
            return self.by_alias(name)

    def random(self) -> Music:
        return random.choice(self)

    def filter(self,
               *,
               level: str | list[str] | None = None,
               ds: float | list[float] | tuple[float, float] | None = None,
               title_search: str | None = None,
               artist_search: str | None = None,
               charter_search: str | None = None,
               genre: str | list[str] | None = None,
               bpm: float | list[float] | tuple[float, float] | None = None,
               type_: str | list[str] | None = None,
               diff: list[int] | None = None,
               ) -> 'MusicList':
        new_list = MusicList()
        for music in self:
            diff2: list[int] = diff if diff is not None else list(range(music.diff_num))
            ret, diff2 = _cross(music.level, level, diff2)
            if not ret:
                continue
            ret, diff2 = _cross(music.ds, ds, diff2)
            if not ret:
                continue
            ret, diff2 = _search_charts(music.charts, charter_search, diff2)
            if not ret:
                continue
            if not _in_or_equal(music.genre, genre):
                continue
            if not _in_or_equal(music.type, type_):
                continue
            if not _in_or_equal(music.bpm, bpm):
                continue
            if title_search is not None and title_search.lower() not in music.title.lower():
                continue
            if artist_search is not None and artist_search.lower() not in music.artist.lower():
                continue
            music: Music = copy.deepcopy(music)
            music.diff = diff2
            new_list.append(music)
        return new_list

    @property
    def max_ds(self) -> float:
        return max(max(music.ds) for music in self)

    @property
    def min_ds(self) -> float:
        return min(min(music.ds) for music in self)


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
        cls.music_list = MusicList.from_json(music_data)
        for music in cls.music_list:
            for i, stats_dict in enumerate(chart_stats['charts'][music.id]):
                if stats_dict:
                    music.charts[i].stats = Stats(stats_dict)

        cls.hot_music_list = MusicList(
            sorted(cls.music_list,
                   key=lambda music: sum(chart.stats.cnt for chart in music.charts),
                   reverse=True)[:128]
        )

    @classmethod
    async def get_aliases(cls) -> None:
        async with aiofiles.open(plugin_config.data_path / 'aliases.json', 'r', encoding='utf-8') as fp:
            obj: dict = json.loads(await fp.read())
        for music in cls.music_list:
            if music.id in obj:
                music.aliases = obj[music.id]['aliases']
            else:
                music.aliases = {}
