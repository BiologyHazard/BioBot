# import nonebot
import asyncio
import re

from nonebot import get_driver, on_regex
from nonebot.adapters.onebot.v11 import Bot, Event
from nonebot.plugin import PluginMetadata

from .data_source import get_av_data

__plugin_meta__ = PluginMetadata(
    name='bilibili视频链接解析',
    description='',
    usage='发送一条带有 av号/bv号/视频链接 的消息，bot会发送视频卡片'
)

global_config = get_driver().config
config = global_config.dict()
b_sleep_time = config.get('b_sleep_time', 2)
b_sleep_time = int(b_sleep_time)


biliav = on_regex(
    r"[Aa][Vv]\d{1,12}|[Bb][Vv]1[A-Za-z0-9]{2}4.1.7[A-Za-z0-9]{2}|[Bb]23\.[Tt][Vv]/[A-Za-z0-9]{7}")


@biliav.handle()
async def handle(bot: Bot, event: Event):
    avcode_list: list[str] = re.compile(
        r"[Aa][Vv]\d{1,12}|[Bb][Vv]1[A-Za-z0-9]{2}4.1.7[A-Za-z0-9]{2}|[Bb]23\.[Tt][Vv]/[A-Za-z0-9]{7}").findall(
        str(event.get_message()))
    if not avcode_list:
        return
    rj_list: list[str] = await get_av_data(avcode_list)
    # await bot.send(event=event, message=repr(rj_list))
    for rj in rj_list:
        await bot.send(event=event, message=rj)
        await asyncio.sleep(b_sleep_time)
