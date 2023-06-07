import asyncio
import copy
import json
import random
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any, Literal, Self, overload

import aiofiles
import aiohttp
from nonebot import logger

from .config import plugin_config
from .consts import GENRE_HAN, LEVELS, VERSION_TO_PLATE


@dataclass
class ChartStats:
    count: int
    diff: str
    fit_diff: float
    avg_achievement: float
    avg_dx_score: float
    std_dev: float
    dist: list[int]
    fc_dist: list[int]

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Self:
        return cls(
            count=int(obj['cnt']),
            diff=obj['diff'],
            fit_diff=obj['fit_diff'],
            avg_achievement=obj['avg'],
            avg_dx_score=obj['avg_dx'],
            std_dev=obj['std_dev'],
            dist=[int(x) for x in obj['dist']],
            fc_dist=[int(x) for x in obj['fc_dist']],
        )

        # self.count: int = int(obj['cnt'])
        # self.diff: str = obj['diff']
        # self.fit_diff: float = obj['fit_diff']
        # self.avg_achievement: float = obj['avg']
        # self.avg_dx_score: float = obj['avg_dx']
        # self.std_dev: float = obj['std_dev']
        # self.dist: list[int] = [int(x) for x in obj['dist']]
        # self.fc_dist: list[int] = [int(x) for x in obj['fc_dist']]

    # def __repr__(self) -> str:
    #     return f'''{self.__class__.__name__}({', '.join(f'{k}={repr(v)}' for k, v in self.__dict__.items())})'''


@dataclass
class Chart:
    is_dx: bool
    tap: int
    hold: int
    slide: int
    touch: int
    break_: int
    notes: int
    max_dx_score: int
    charter: str
    stats: ChartStats = field(init=False)

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Self:
        return cls(
            is_dx=len(obj['notes']) == 5,
            tap=obj['notes'][0],
            hold=obj['notes'][1],
            slide=obj['notes'][2],
            touch=obj['notes'][3] if len(obj['notes']) == 5 else 0,
            break_=obj['notes'][-1],
            notes=sum(obj['notes']),
            max_dx_score=sum(obj['notes']) * 3,
            charter=obj['charter'],
        )


@dataclass
class Music:
    id: str
    title: str
    type: str
    ds: list[float]
    level: list[str]
    diff_num: int
    has_remaster: bool
    artist: str
    genre: str
    genre_han: str
    bpm: float
    release_date: str
    version: str
    version_han: str
    charts: list[Chart]
    diff: list[int]
    aliases: dict[str, dict[str, Any]] = field(init=False)

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Self:
        return cls(
            id=obj['id'],
            title=obj['title'],
            type=obj['type'],
            ds=obj['ds'],
            level=obj['level'],
            diff_num=len(obj['level']),
            has_remaster=(len(obj['level']) == 5),
            artist=obj['basic_info']['artist'],
            genre=obj['basic_info']['genre'],
            genre_han=GENRE_HAN[obj['basic_info']['genre']],
            bpm=obj['basic_info']['bpm'],
            release_date=obj['basic_info']['release_date'],
            version=obj['basic_info']['from'],
            version_han=VERSION_TO_PLATE[obj['basic_info']['from']],
            charts=[Chart.from_json(chart) for chart in obj['charts']],
            diff=list(range(len(obj['level'])))
        )


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
    def from_json(cls, obj: list[dict[str, Any]]) -> Self:
        return cls(Music.from_json(music) for music in obj)

    @overload
    def by_id(self, name: str, strict: Literal[False] = ...) -> Music | None: ...

    @overload
    def by_id(self, name: str, strict: Literal[True] = ...) -> Music: ...

    def by_id(self, name: str, strict: bool = False) -> Music | None:
        if name and name.isdigit():
            for music in self:
                if music.id == name:
                    return music
        if strict:
            raise ValueError(f'Music of id{name} not found.')
        return None

    # def by_title(self, music_title: str) -> Music | None:
    #     for music in self:
    #         if music.title == music_title:
    #             return music
    #     return None

    def by_alias(self, name: str) -> Self:
        '''标题的字串也可以，对大小写和空格不敏感'''
        name = name.strip().replace(' ', '').lower()
        if not name:
            return self.__class__()
        return self.__class__(music for music in self
                              if name in music.title.replace(' ', '').lower()
                              or any(alias.strip().replace(' ', '').lower() == name for alias in music.aliases))

    def by_name(self, name: str) -> Self:
        if name.isdigit() and (music := Mai.music_list.by_id(name)) is not None:
            return self.__class__([music])
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
               ) -> Self:
        new_list = self.__class__()
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


@dataclass
class LevelStats:
    avg_count: float
    avg_achievement: float
    avg_std_dev: float
    avg_dx_score_ratio: float
    dist: list[float]
    fc_dist: list[float]


class Mai:
    music_list: MusicList
    hot_music_list: MusicList
    diff_data: dict[str, LevelStats]

    @classmethod
    async def get_music(cls) -> None:
        async def get_music_data() -> Any:
            logger.info('正在获取乐曲信息...')
            try:
                async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/music_data') as response:
                    assert response.status == 200
                    obj: Any = await response.json()
                    async with aiofiles.open(plugin_config.data_path / 'music_data.json', 'w', encoding='utf-8') as fp:
                        await fp.write(json.dumps(obj, ensure_ascii=False))
            except Exception:
                logger.warning('乐曲信息获取失败，请检查网络环境。已切换至本地暂存文件。')
                async with aiofiles.open(plugin_config.data_path / 'music_data.json', 'r', encoding='utf-8') as fp:
                    obj = json.loads(await fp.read())
            return obj

        async def get_chart_stats() -> Any:
            logger.info('正在获取谱面统计...')
            try:
                async with aiohttp.request('GET', 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as response:
                    assert response.status == 200
                    obj: Any = await response.json()
                    async with aiofiles.open(plugin_config.data_path / 'chart_stats.json', 'w', encoding='utf-8') as fp:
                        await fp.write(json.dumps(obj, ensure_ascii=False))
            except Exception:
                logger.warning('谱面统计获取失败，请检查网络环境。已切换至本地暂存文件。')
                async with aiofiles.open(plugin_config.data_path / 'chart_stats.json', 'r', encoding='utf-8') as fp:
                    obj = json.loads(await fp.read())
            return obj

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
                    music.charts[i].stats = ChartStats.from_json(stats_dict)

        cls.hot_music_list = MusicList(
            sorted(cls.music_list,
                   key=lambda music: sum(chart.stats.count for chart in music.charts),
                   reverse=True)[:128]
        )

        count: defaultdict[str, int] = defaultdict(int)
        count_sum: defaultdict[str, int] = defaultdict(int)
        std_dev_sum: defaultdict[str, float] = defaultdict(float)
        dx_score_ratio_sum: defaultdict[str, float] = defaultdict(float)
        for music in cls.music_list:
            for i in range(music.diff_num):
                level: str = music.level[i]
                count[level] += 1
                chart: Chart = music.charts[i]
                stats: ChartStats = chart.stats
                count_sum[level] += stats.count
                std_dev_sum[level] += stats.std_dev
                dx_score_ratio_sum[level] += stats.avg_dx_score / chart.max_dx_score

        cls.diff_data = {}
        for level in LEVELS:
            level_diff_data: dict[str, Any] = chart_stats['diff_data'][level]
            cls.diff_data[level] = LevelStats(
                avg_count=count_sum[level] / count[level],
                avg_achievement=level_diff_data['achievements'],
                avg_std_dev=std_dev_sum[level] / count[level],
                avg_dx_score_ratio=dx_score_ratio_sum[level] / count[level],
                dist=level_diff_data['dist'],
                fc_dist=level_diff_data['fc_dist'],
            )

    @classmethod
    async def get_aliases(cls) -> None:
        logger.info('正在获取别名信息...')
        async with aiofiles.open(plugin_config.data_path / 'aliases.json', 'r', encoding='utf-8') as fp:
            obj: dict = json.loads(await fp.read())
        for music in cls.music_list:
            if music.id in obj:
                music.aliases = obj[music.id]['aliases']
            else:
                music.aliases = {}
