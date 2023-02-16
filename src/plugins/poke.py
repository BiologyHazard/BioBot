from nonebot import on_notice
from nonebot.adapters.onebot.v11 import Message, Event, Bot, MessageSegment


async def _poke(bot: Bot, event: Event) -> bool:
    value = (event.notice_type == "notify" and event.sub_type ==
             "poke" and event.target_id == int(bot.self_id))
    return value

poke = on_notice(rule=_poke, priority=10, block=True)


@poke.handle()
async def poke_func(event: Event):
    # if event.__getattribute__('group_id') is None:
    #     event.__delattr__('group_id')
    await poke.send(Message([MessageSegment("poke", {"qq": f"{event.sender_id}"})]))
