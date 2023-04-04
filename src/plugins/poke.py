from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Message, Bot, MessageSegment, PokeNotifyEvent
from typing import NoReturn


async def _poke(bot: Bot, event: PokeNotifyEvent) -> bool:
    return event.target_id == int(bot.self_id)

poke = on_notice(rule=_poke, priority=10, block=True)


@poke.handle()
async def poke_func(event: PokeNotifyEvent) -> NoReturn:
    await poke.finish(Message([MessageSegment("poke", {"qq": f"{event.user_id}"})]))
