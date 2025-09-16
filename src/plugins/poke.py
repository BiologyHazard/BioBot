from datetime import datetime, timedelta

from nonebot import logger, on_notice, on_command
from nonebot.adapters.onebot.v11 import Bot, MessageSegment, PokeNotifyEvent, MessageEvent, GroupMessageEvent, PrivateMessageEvent
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

__plugin_meta__ = PluginMetadata(
    name='戳一戳',
    description='戳bot一下，bot戳你一下；戳别人一下，bot跟着戳一下',
    usage='戳bot一下，bot戳你一下；戳别人一下，bot跟着戳一下'
)

# 冷却时间（秒）
COOLDOWN_TIME = timedelta(seconds=60)
# 记录冷却时间的字典
last_poke_time = datetime.now().astimezone() - COOLDOWN_TIME


@Rule
async def not_poked_by_self_and_cooled_down(event: PokeNotifyEvent) -> bool:
    if event.group_id is None:  # 私聊
        sender_id = event.sender_id  # type: ignore
    else:  # 群聊
        sender_id = event.user_id
    if sender_id == event.self_id:  # 自己戳任何人
        return False

    # 否则是别人戳任何人，此时检查冷却时间
    global last_poke_time

    now = datetime.now().astimezone()
    result = now - last_poke_time > COOLDOWN_TIME
    if result:
        last_poke_time = now
    else:
        logger.opt(colors=True).info(f"收到戳一戳消息，但是<yellow><bold>冷却时间未到</></>，当前时间：{now}，上次戳的时间：{last_poke_time}，冷却时间：{COOLDOWN_TIME}，冷却时间还剩：{COOLDOWN_TIME - (now - last_poke_time)}")

    return result


poke = on_notice(rule=not_poked_by_self_and_cooled_down, priority=10, block=False)
poke_me = on_command("戳我", priority=10, block=False)
poke_self = on_command("戳自己", priority=10, block=False)


async def send_poke(bot, group_id, user_id):
    if group_id is None:  # 私聊
        await bot.friend_poke(user_id=user_id)
    else:  # 群聊
        await bot.group_poke(group_id=group_id, user_id=user_id)


@poke.handle()
async def poke_func(bot: Bot, event: PokeNotifyEvent):
    if event.user_id == event.self_id:  # 自己戳任何人
        return

    if event.target_id == event.self_id:  # 别人戳自己
        await send_poke(bot, event.group_id, event.user_id)

    else:  # 别人戳别人
        await send_poke(bot, event.group_id, event.target_id)


@poke_me.handle()
async def poke_me_func(bot: Bot, event: MessageEvent):
    await send_poke(bot, getattr(event, "group_id", None), event.user_id)


@poke_self.handle()
async def poke_self_func(bot: Bot, event: GroupMessageEvent):  # 私聊不能戳自己
    await send_poke(bot, event.group_id, event.self_id)
