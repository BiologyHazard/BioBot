# import json
import random
import aiohttp
import os
from typing import Dict, List, Optional, Union, Tuple, Any
from copy import deepcopy
from retrying import retry
from collections import defaultdict
import requests


def get_cover_len4_id(mid) -> str:
    mid = int(mid)
    if 10001 <= mid:
        mid -= 10000
    return f'{mid:04d}'


def cross(checker: List[Any], elem: Optional[Union[Any, List[Any]]], diff):
    ret = False
    diff_ret = []
    if not elem or elem is Ellipsis:
        return True, diff
    if isinstance(elem, List):
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if __e in elem:
                diff_ret.append(_j)
                ret = True
    elif isinstance(elem, Tuple):
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem[0] <= __e <= elem[1]:
                diff_ret.append(_j)
                ret = True
    else:
        for _j in (range(len(checker)) if diff is Ellipsis else diff):
            if _j >= len(checker):
                continue
            __e = checker[_j]
            if elem == __e:
                return True, [_j]
    return ret, diff_ret


def in_or_equal(checker: Any, elem: Optional[Union[Any, List[Any]]]):
    if elem is Ellipsis:
        return True
    if isinstance(elem, List):
        return checker in elem
    elif isinstance(elem, Tuple):
        return elem[0] <= checker <= elem[1]
    else:
        return checker == elem


class Stats(Dict):
    count: Optional[int] = None
    avg: Optional[float] = None
    sss_count: Optional[int] = None
    difficulty: Optional[str] = None
    rank: Optional[int] = None
    total: Optional[int] = None

    def __getattribute__(self, item):
        try:
            if item == 'sss_count':
                return self['sssp_count']
            elif item == 'rank':
                return self['v'] + 1
            elif item == 'total':
                return self['t']
            elif item == 'difficulty':
                return self['tag']
            elif item in self:
                return self[item]
            return super().__getattribute__(item)
        except KeyError:
            return 'Unknown'


class Chart(Dict):
    tap: Optional[int] = None
    slide: Optional[int] = None
    hold: Optional[int] = None
    touch: Optional[int] = None
    brk: Optional[int] = None
    charter: Optional[int] = None

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


class Music(Dict):
    id: Optional[str] = None
    title: Optional[str] = None
    ds: Optional[List[float]] = None
    level: Optional[List[str]] = None
    genre: Optional[str] = None
    type: Optional[str] = None
    bpm: Optional[float] = None
    version: Optional[str] = None
    charts: Optional[Chart] = None
    release_date: Optional[str] = None
    artist: Optional[str] = None

    diff: List[int] = []

    def __getattribute__(self, item):
        if item in {'genre', 'artist', 'release_date', 'bpm', 'version'}:
            if item == 'version':
                return self['basic_info']['from']
            return self['basic_info'][item]
        elif item in self:
            return self[item]
        return super().__getattribute__(item)


class MusicList(List[Music]):
    def by_id(self, music_id: str) -> Optional[Music]:
        for music in self:
            if music.id == music_id:
                return music
        return None

    def by_title(self, music_title: str) -> Optional[Music]:
        for music in self:
            if music.title == music_title:
                return music
        return None

    def random(self):
        return random.choice(self)

    def filter(self,
               *,
               level: Optional[Union[str, List[str]]] = ...,
               ds: Optional[Union[float, List[float],
                                  Tuple[float, float]]] = ...,
               title_search: Optional[str] = ...,
               genre: Optional[Union[str, List[str]]] = ...,
               bpm: Optional[Union[float, List[float],
                                   Tuple[float, float]]] = ...,
               type: Optional[Union[str, List[str]]] = ...,
               diff: List[int] = ...,
               ):
        new_list = MusicList()
        for music in self:
            diff2 = diff
            music = deepcopy(music)
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
            if title_search is not Ellipsis and title_search.lower() not in music.title.lower():
                continue
            music.diff = diff2
            new_list.append(music)
        return new_list


obj = requests.get(
    'https://www.diving-fish.com/api/maimaidxprober/music_data').json()
total_list: MusicList = MusicList(obj)
for __i in range(len(total_list)):
    total_list[__i] = Music(total_list[__i])
    for __j in range(len(total_list[__i].charts)):
        total_list[__i].charts[__j] = Chart(total_list[__i].charts[__j])


@retry(stop_max_attempt_number=3)
# async def get_music_list() -> MusicList:
async def get_music_list() -> MusicList:
    """
    获取所有数据
    """
    async with aiohttp.request("GET", 'https://www.diving-fish.com/api/maimaidxprober/music_data') as obj_data:
        if obj_data.status != 200:
            raise aiohttp.ClientResponseError('maimaiDX曲目数据获取失败，请检查网络环境')
        else:
            data = await obj_data.json()
    async with aiohttp.request("GET", 'https://www.diving-fish.com/api/maimaidxprober/chart_stats') as obj_stats:
        if obj_stats.status != 200:
            raise aiohttp.ClientResponseError('maimaiDX数据获取错误，请检查网络环境')
        else:
            stats = await obj_stats.json()

    total_list: MusicList = MusicList(data)
    for i in range(len(total_list)):
        total_list[i] = Music(total_list[i])
        total_list[i]['stats'] = stats[total_list[i].id]
        for j in range(len(total_list[i].charts)):
            total_list[i].charts[j] = Chart(total_list[i].charts[j])
            total_list[i].stats[j] = Stats(total_list[i].stats[j])
    return total_list


class MaiMusic:

    total_list: Optional[MusicList]

    def __init__(self) -> None:
        """
        封装所有曲目信息以及猜歌数据，便于更新
        """

    async def get_music(self) -> None:
        """
        获取所有曲目数据
        """
        self.total_list = await get_music_list()

    # def aliases(self):
    #     """
    #     初始化所有别名数据
    #     """
    #     self.music_aliases, self.music_aliases_reverse, self.music_aliases_lines = self.__music_aliases__()

    # def __music_aliases__(self):
    #     _music_aliases = defaultdict(list)
    #     _music_aliases_reverse = defaultdict(list)
    #     with open(os.path.join(static, 'aliases.csv'), 'r', encoding='utf-8') as f:
    #         _music_aliases_lines = f.readlines()
    #     for l in _music_aliases_lines:
    #         arr = l.strip().split('\t')
    #         for i in range(len(arr)):
    #             if arr[i] != '':
    #                 _music_aliases[arr[i].lower()].append(arr[0])
    #                 _music_aliases_reverse[arr[0]].append(arr[i].lower())
    #     return _music_aliases, _music_aliases_reverse, _music_aliases_lines

    # def save_aliases(self, data: str):
    #     with open(aliases_csv, 'w', encoding='utf-8') as f:
    #         f.write(data)
    #     self.aliases()

    # def guess(self):
    #     """
    #     初始化猜歌数据
    #     """
    #     self.guess_data = list(
    #         filter(lambda x: x['id'] in hot_music_ids, mai.total_list))


mai = MaiMusic()
