import asyncio
import copy
import json
import math
import random
import time
from bisect import bisect_right
from collections import defaultdict
from dataclasses import dataclass, field
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, Self, Sequence, overload

import aiofiles
import aiohttp
from nonebot import logger

from .config import plugin_config
from .consts import (LEVELS, PLATE_TO_VERSION, VERSION_TO_PLATE, BaseRaSpp,
                     achievementList)


def calc_rating(ds: float, achievement: float) -> int:
    return math.floor(ds * min(achievement, 100.5000) * BaseRaSpp[bisect_right(achievementList, achievement)] / 100)


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

    # @classmethod
    # def empty(cls) -> Self:
    #     return cls(
    #         count=0,
    #         diff='0',
    #         fit_diff=0,
    #         avg_achievement=0,
    #         avg_dx_score=0,
    #         std_dev=0,
    #         dist=[],
    #         fc_dist=[],
    #     )


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
class AliasInfo:
    group: int
    qqid: int
    nickname: str
    card: str
    role: str
    time: int

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Self:
        return cls(
            group=obj['group'],
            qqid=obj['qqid'],
            nickname=obj['nickname'],
            card=obj['card'],
            role=obj['role'],
            time=obj['time'],
        )


def get_cover_filename(music_id: str) -> str:
    num = int(music_id)
    if 10000 < num <= 11000:
        num -= 10000
    return f'{num:05d}.png'


async def get_music_cover(music_id: str) -> BytesIO:
    '''获取封面'''
    filename = get_cover_filename(music_id)
    cover_path: Path = plugin_config.cover_path / filename
    try:
        if cover_path.is_file():
            async with aiofiles.open(cover_path, 'rb') as fp:
                # 从本地图片读取
                return BytesIO(await fp.read())

        async with aiohttp.request('GET', f'https://www.diving-fish.com/covers/{filename}') as response:
            response.raise_for_status()
            cover_bytes: bytes = await response.read()
            async with aiofiles.open(cover_path, 'wb') as fp:
                await fp.write(cover_bytes)
            # 从水鱼网下载
            return BytesIO(cover_bytes)

    except Exception:
        async with aiofiles.open(plugin_config.cover_path / '00000.png', 'rb') as fp:
            # 返回'00000.png'
            return BytesIO(await fp.read())


async def get_music_track(music_id: str) -> BytesIO:
    if music_id in Mai.track_path:
        path = plugin_config.chart_path / Mai.track_path[music_id]
    else:
        path = plugin_config.chart_path / 'audio_resources_not_found.mp3'
    async with aiofiles.open(path, 'rb') as fp:
        return BytesIO(await fp.read())


@dataclass
class Music:
    id: str
    title: str
    type: str
    ds: list[float]
    level: list[str]
    diff_num: int = field(init=False)
    has_remaster: bool = field(init=False)
    artist: str
    genre: str
    bpm: float
    release_date: str
    version: str
    version_han: str = field(init=False)
    charts: list[Chart]
    diff: list[int] = field(init=False)
    aliases: dict[str, AliasInfo] = field(init=False)

    @classmethod
    def from_json(cls, obj: dict[str, Any]) -> Self:
        return cls(
            id=obj['id'],
            title=obj['title'],
            type=obj['type'],
            ds=obj['ds'],
            level=obj['level'],
            artist=obj['basic_info']['artist'],
            genre=obj['basic_info']['genre'],
            bpm=obj['basic_info']['bpm'],
            release_date=obj['basic_info']['release_date'],
            version=obj['basic_info']['from'],
            charts=[Chart.from_json(chart) for chart in obj['charts']],
        )

    def __post_init__(self) -> None:
        self.diff_num = len(self.level)
        self.has_remaster = self.diff_num == 5
        self.diff = list(range(self.diff_num))
        self.version_han = VERSION_TO_PLATE[self.version]

    async def get_cover(self) -> BytesIO:
        return await get_music_cover(self.id)

    async def get_track(self) -> BytesIO:
        return await get_music_track(self.id)


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
        # if hasattr(self, 'id_to_index') and self._id_to_index[name].id == name:
        #     return self._id_to_index[name]
        # else:
        #     self._id_to_index: dict[str, Music] = {music.id: music for music in self}

        if name and name.isdigit():
            for music in self:
                if music.id == name:
                    return music
        if strict:
            raise ValueError(f'Music of id{name} not found.')
        return None

    def by_title(self, name: str) -> Self:
        name = name.strip().replace(' ', '').lower()
        if not name:
            return self.__class__()
        return self.__class__(music for music in self
                              if name.replace(' ', '').lower() in music.title.replace(' ', '').lower())

    def by_type(self, name: str) -> Self:
        return self.__class__(music for music in self
                              if name == music.type)

    def by_ds(self, name: float | Sequence[float] | tuple[float, float]) -> list[tuple[Music, int]]:
        '''这里浮点数不会出事'''
        if isinstance(name, float):
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if math.isclose(name, music.ds[diff_index])]
        elif isinstance(name, tuple) and len(name) == 2:
            x, y = name
            if x > y:
                return []
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if x <= music.ds[diff_index] <= y]
        elif isinstance(name, Sequence):
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if any(math.isclose(ds, music.ds[diff_index]) for ds in name)]
        else:
            raise TypeError("type of param 'name' must be float | Sequence[float] | tuple[float, float]")

    def by_level(self, name: str | Sequence[str] | tuple[str, str]) -> list[tuple[Music, int]]:
        if isinstance(name, str):
            if name not in LEVELS:
                return []
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if name == music.level[diff_index]]
        elif isinstance(name, tuple) and len(name) == 2:
            x, y = name
            if x not in LEVELS or y not in LEVELS:
                return []
            x_index: int = LEVELS.index(x)
            y_index: int = LEVELS.index(y)
            if x > y:
                return []
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if x_index <= LEVELS.index(music.level[diff_index]) <= y_index]
        elif isinstance(name, Sequence):
            return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                    if any(level == music.level[diff_index] for level in name)]
        else:
            raise TypeError("type of param 'name' must be str | Sequence[str] | tuple[str, str]")

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

    def by_artist(self, name: str) -> Self:
        name = name.strip().replace(' ', '').lower()
        if not name:
            return self.__class__()
        return self.__class__(music for music in self
                              if name in music.artist.replace(' ', '').lower())

    def by_charter(self, name: str) -> list[tuple[Music, int]]:
        name = name.strip().replace(' ', '').lower()
        if not name:
            return []
        return [(music, diff_index) for music in self for diff_index in range(music.diff_num)
                if name in music.charts[diff_index].charter.replace(' ', '').lower()]

    def by_genre(self, name: str) -> Self:
        return self.__class__(music for music in self
                              if name == music.genre)

    def by_bpm(self, name: float | Sequence[float] | tuple[float, float]) -> Self:
        '''bpm都是整数，浮点数不会出事（大概）'''
        if isinstance(name, float):
            return self.__class__(music for music in self
                                  if math.isclose(name, music.bpm))
        elif isinstance(name, tuple) and len(name) == 2:
            x, y = name
            if x > y:
                return self.__class__()
            return self.__class__(music for music in self
                                  if x <= music.bpm <= y)
        elif isinstance(name, Sequence):
            return self.__class__(music for music in self
                                  if any(math.isclose(bpm, music.bpm) for bpm in name))
        else:
            raise TypeError("type of param 'name' must be float | Sequence[float] | tuple[float, float]")

    def by_version(self, name: str | Sequence[str]) -> Self:
        if isinstance(name, str):
            if name in VERSION_TO_PLATE:
                return self.__class__(music for music in self if name == music.version)
            elif name in PLATE_TO_VERSION:
                return self.by_version(PLATE_TO_VERSION[name])
            return self.__class__()
        else:
            versions: list[str] = []
            for version in name:
                if version in VERSION_TO_PLATE:
                    versions.append(version)
                elif version in PLATE_TO_VERSION:
                    versions.extend(PLATE_TO_VERSION[version])
            return self.__class__(music for music in self
                                  if any(version == music.version for version in versions))

    def random(self) -> Music:
        return random.choice(self)

    def filter(self,
               *,
               level: str | Sequence[str] | None = None,
               ds: float | Sequence[float] | tuple[float, float] | None = None,
               title_search: str | None = None,
               artist_search: str | None = None,
               charter_search: str | None = None,
               genre: str | Sequence[str] | None = None,
               bpm: float | Sequence[float] | tuple[float, float] | None = None,
               type_: str | Sequence[str] | None = None,
               version: str | Sequence[str] | None = None,
               diff: list[int] | None = None,
               ) -> Self:
        logger.warning('MusicList.filter() method is deprecated. Use MusicList.by_*() instead.')
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
            if not _in_or_equal(music.version, version):
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

    def get_other_type(self, music: Music) -> Music | None:
        possible_musics: list[Music] = [
            x for x in self
            if music.title == x.title and music.artist == x.artist and music.genre == x.genre
            and music.id != x.id and music.type != x.type
        ]
        if len(possible_musics) == 1:
            return possible_musics[0]
        return None


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
                    response.raise_for_status()
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
                    response.raise_for_status()
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
            if music.id in chart_stats['charts']:
                for i, stats_dict in enumerate(chart_stats['charts'][music.id]):
                    if stats_dict:
                        music.charts[i].stats = ChartStats.from_json(stats_dict)

            #     for i in range(music.diff_num):
            #         stats_dict = chart_stats['charts'][music.id][i]
            #         if stats_dict:
            #             music.charts[i].stats = ChartStats.from_json(stats_dict)
            #         else:
            #             music.charts[i].stats = ChartStats.empty()
            # else:
            #     for i in range(music.diff_num):
            #         music.charts[i].stats = ChartStats.empty()

        cls.hot_music_list = MusicList(
            sorted(cls.music_list,
                   key=lambda music: sum(chart.stats.count if hasattr(chart, 'stats') else 0
                                         for chart in music.charts[2:]),
                   reverse=True)[:128]
        )

        count: defaultdict[str, int] = defaultdict(int)
        count_sum: defaultdict[str, int] = defaultdict(int)
        std_dev_sum: defaultdict[str, float] = defaultdict(float)
        dx_score_ratio_sum: defaultdict[str, float] = defaultdict(float)
        for music in cls.music_list:
            for i in range(music.diff_num):
                level: str = music.level[i]
                chart: Chart = music.charts[i]
                if not hasattr(chart, 'stats'):
                    continue
                count[level] += 1
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

        if (plugin_config.data_path / 'track_path.json').is_file():
            async with aiofiles.open(plugin_config.data_path / 'track_path.json', 'r', encoding='utf-8') as fp:
                cls.track_path: dict[str, str] = json.loads(await fp.read())
        else:
            cls.track_path = {}

    @classmethod
    async def get_aliases(cls) -> None:
        logger.info('正在获取别名信息...')
        if (plugin_config.data_path / 'aliases.json').is_file():
            async with aiofiles.open(plugin_config.data_path / 'aliases.json', 'r', encoding='utf-8') as fp:
                obj: dict = json.loads(await fp.read())
            for music in cls.music_list:
                if music.id in obj:
                    music.aliases = {alias: AliasInfo.from_json(alias_info)
                                     for alias, alias_info in obj[music.id]['aliases'].items()}
                else:
                    music.aliases = {}

        try:
            async with aiohttp.request('GET', 'https://api.yuzuai.xyz/maimaidx/MaimaiDXAlias') as response:
                response.raise_for_status()
                obj = await response.json()
                async with aiofiles.open(plugin_config.data_path / 'aliases_from_yuzuai_api.json', 'w', encoding='utf-8') as fp:
                    await fp.write(json.dumps(obj, ensure_ascii=False))
        except Exception:
            logger.warning('别名信息获取失败，请检查网络环境。已切换至本地暂存文件。')
            async with aiofiles.open(plugin_config.data_path / 'aliases_from_yuzuai_api.json', 'r', encoding='utf-8') as fp:
                obj = json.loads(await fp.read())

        for music_id, aliases_dict in obj.items():
            music: Music = cls.music_list.by_id(music_id, strict=True)
            for alias in aliases_dict['Alias']:
                if alias.strip().lower() == music.title.strip().lower():
                    continue
                music.aliases[alias] = AliasInfo(group=0, qqid=0, nickname='Yuzuai API', card='Yuzuai API', role='owner', time=int(time.time()))
