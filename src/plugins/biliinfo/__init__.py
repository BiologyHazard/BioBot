import asyncio
import re

from nonebot import on_regex
from nonebot.params import EventPlainText
from nonebot.plugin import PluginMetadata

from .config import plugin_config
from .data_source import T_group, get_video_info

__plugin_meta__ = PluginMetadata(
    name='bilibili视频链接解析',
    description='',
    usage='发送一条带有 av号/bv号/视频链接 的消息，bot会发送视频卡片'
)


show_info = on_regex(r'BV1\w{9}|b23\.(?:tv|wtf)\/\w{7}|av\d+', flags=re.RegexFlag.IGNORECASE + re.RegexFlag.ASCII)


@show_info.handle()
async def show_info_func(message: str = EventPlainText()):
    # avcode_list: list[str] = re.compile(
    #     r"[Aa][Vv]\d{1,12}|[Bb][Vv]1[A-Za-z0-9]{2}4.1.7[A-Za-z0-9]{2}|[Bb]23\.[Tt][Vv]/[A-Za-z0-9]{7}").findall(
    #     str(event.get_message()))
    # if not avcode_list:
    #     return
    # rj_list: list[str] = await get_av_data(avcode_list)
    # # await bot.send(event=event, message=repr(rj_list))
    # for rj in rj_list:
    #     await bot.send(event=event, message=rj)
    #     await asyncio.sleep(b_sleep_time)
    groups: list[T_group] = re.findall(r'(?:b23\.(?:tv|wtf)\/)?(?:(BV1\w{9})|(av\d+))|(b23\.(?:tv|wtf)\/\w{7})', message)
    for group in groups[:plugin_config.biliinfo_max_count]:
        await asyncio.gather(show_info.send(await get_video_info(group)), asyncio.sleep(plugin_config.biliinfo_sleep_time))
