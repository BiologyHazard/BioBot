import time
from .config import plugin_config
from typing import Any
import aiohttp
import math
import re
from nonebot import logger
from nonebot.adapters.onebot.v11 import MessageSegment, Message

url: str = 'https://api.bilibili.com/x/web-interface/view'

T_group = tuple[str, str, str]
'''(BV, b23, av)'''


async def b23_to_bv(b23: str) -> str:
    async with aiohttp.request('GET', f'https://{b23}') as response:
        return re.findall(r'BV1\w{2}4\w1\w7\w{2}', str(response.url))[0]


def bv_to_av(bv: str) -> int:
    # 1.去除Bv号前的"Bv"字符
    BvNo1: str = bv[2:]
    keys: dict[str, str] = {
        '1': '13', '2': '12', '3': '46', '4': '31', '5': '43', '6': '18', '7': '40', '8': '28',
        '9': '5', 'A': '54', 'B': '20', 'C': '15', 'D': '8', 'E': '39', 'F': '57', 'G': '45',
        'H': '36', 'J': '38', 'K': '51', 'L': '42', 'M': '49', 'N': '52', 'P': '53', 'Q': '7',
        'R': '4', 'S': '9', 'T': '50', 'U': '10', 'V': '44', 'W': '34', 'X': '6', 'Y': '25',
        'Z': '1', 'a': '26', 'b': '29', 'c': '56', 'd': '3', 'e': '24', 'f': '0', 'g': '47',
        'h': '27', 'i': '22', 'j': '41', 'k': '16', 'm': '11', 'n': '37', 'o': '2', 'p': '35',
        'q': '21', 'r': '17', 's': '33', 't': '30', 'u': '48', 'v': '23', 'w': '55', 'x': '32',
        'y': '14', 'z': '19'

    }
    # 2. 将key对应的value存入一个列表
    BvNo2: list[int] = []
    for ch in BvNo1:
        BvNo2.append(int(str(keys[ch])))
    # 3. 对列表中不同位置的数进行*58的x次方的操作
    BvNo2[0] = int(BvNo2[0] * math.pow(58, 6))
    BvNo2[1] = int(BvNo2[1] * math.pow(58, 2))
    BvNo2[2] = int(BvNo2[2] * math.pow(58, 4))
    BvNo2[3] = int(BvNo2[3] * math.pow(58, 8))
    BvNo2[4] = int(BvNo2[4] * math.pow(58, 5))
    BvNo2[5] = int(BvNo2[5] * math.pow(58, 9))
    BvNo2[6] = int(BvNo2[6] * math.pow(58, 3))
    BvNo2[7] = int(BvNo2[7] * math.pow(58, 7))
    BvNo2[8] = int(BvNo2[8] * math.pow(58, 1))
    BvNo2[9] = int(BvNo2[9] * math.pow(58, 0))
    # 4.求出这10个数的合
    s: int = sum(BvNo2)
    # 5. 将和减去100618342136696320
    s -= 100618342136696320
    # 6. 将sum 与177451812进行异或
    temp: int = 177451812
    return s ^ temp


async def get_top_comments(av: int) -> str:
    try:
        async with aiohttp.request('GET', 'https://api.bilibili.com/x/v2/reply/main', params={'next': '0', 'type': '1', 'oid': str(av)}) as response:
            obj: dict[str, Any] = await response.json()
    except Exception:
        return ''
    hot_comments: list[dict[str, Any]] = obj['data']['replies'][:3]
    msg: str = '\n-----------------\n--前三热评如下--\n-----------------\n'
    for c in hot_comments:
        name: str = c['member']['uname']
        txt: str = c['content']['message']
        msg += f'{name}: {txt}\n\n'
    return msg


async def get_video_info(av: int) -> Message:
    async with aiohttp.request('GET', url, params={'aid': str(av)}) as response:
        assert response.status == 200
        obj: dict[str, Any] = await response.json()

    assert obj['code'] == 0
    bv: str = obj['data']['bvid']
    title: str = obj['data']['title']
    pic_url: str = obj['data']['pic']
    stat: dict[str, Any] = obj['data']['stat']
    view: int = stat['view']
    danmaku: int = stat['danmaku']
    reply: int = stat['reply']
    fav: int = stat['favorite']
    coin: int = stat['coin']
    share: int = stat['share']
    like: int = stat['like']
    link: str = f'https://b23.tv/av{av}'
    desc: str = obj['data']['desc']
    name: str = obj['data']['owner']['name']
    mid: int = obj['data']['owner']['mid']
    up_link: str = f'https://space.bilibili.com/{mid}'
    pub_date: int = obj['data']['pubdate']
    date_str: str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(pub_date))

    message: Message = (
        MessageSegment.image(pic_url)
        + f'av{av} / {bv}\n{title}\nUP主：{name}({up_link})\n投稿时间：{date_str}\n播放：{view} | 弹幕：{danmaku} | 评论：{reply}\n点赞：{like} | 硬币：{coin} | 收藏：{fav} | 分享：{share}\n点击链接进入：\n{link}\n简介：{desc}')

    if plugin_config.biliinfo_show_comments:
        message += await get_top_comments(av)

    return message


async def group_to_info(group: T_group) -> Message:
    bv, b23, str_av = group
    if bv:
        av: int = bv_to_av(bv)
    elif b23:
        bv: str = await b23_to_bv(b23)
        av = bv_to_av(bv)
    elif str_av:
        av = int(str_av[2:])
    else:
        raise ValueError

    return await get_video_info(av)
