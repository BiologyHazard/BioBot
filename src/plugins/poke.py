from typing import NoReturn

from nonebot import on_notice
from nonebot.adapters.onebot.v11 import MessageSegment, PokeNotifyEvent
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

__plugin_meta__ = PluginMetadata(
    name='戳一戳',
    description='戳bot一下，bot戳你一下；戳别人一下，bot跟着戳一下',
    usage='戳bot一下，bot戳你一下；戳别人一下，bot跟着戳一下'
)


@Rule
async def not_poked_by_self(event: PokeNotifyEvent) -> bool:
    return event.user_id != event.self_id


poke = on_notice(rule=not_poked_by_self, priority=10, block=False)


@poke.handle()
async def poke_func(event: PokeNotifyEvent) -> NoReturn:
    if event.target_id == event.self_id:  # 别人戳自己
        await poke.finish(MessageSegment('poke', {'qq': event.user_id}))
    else:  # 别人戳别人
        await poke.finish(MessageSegment('poke', {'qq': event.target_id}))
