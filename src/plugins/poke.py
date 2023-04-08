from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Message, Bot, MessageSegment, PokeNotifyEvent
from typing import NoReturn
# from nonebot.rule import Rule


# @Rule
# async def poke_rule(bot: Bot, event: PokeNotifyEvent) -> bool:
#     return event.target_id == int(bot.self_id)

poke = on_notice(priority=10, block=False)


@poke.handle()
async def poke_func(bot: Bot, event: PokeNotifyEvent) -> NoReturn:
    if event.target_id == int(bot.self_id):
        await poke.finish(MessageSegment('poke', {'qq': event.user_id}))
    else:
        await poke.finish(MessageSegment('poke', {'qq': event.target_id}))
