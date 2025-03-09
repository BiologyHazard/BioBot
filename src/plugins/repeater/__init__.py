from nonebot import get_plugin_config, logger, on_message
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message
from nonebot.params import EventMessage
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .config import Config

__plugin_meta__ = PluginMetadata(
    name='复读机',
    description='bot的本质是复读',
    usage='bot会自动复读重复的群消息'
)

plugin_config = get_plugin_config(Config)

last_message: dict[int, Message] = {}
message_times: dict[int, int] = {}


def _message_preprocess(message: Message) -> Message:
    '''预处理 message, 对于 `CQ:image` 仅保留 `file` 字段'''
    for message_segment in message:
        if message_segment.type == 'image':
            message_segment.data = {'file': message_segment.data['file']}
    return message


@Rule
async def in_repeater_group(event: GroupMessageEvent) -> bool:
    return plugin_config.repeater_group == 'all' or event.group_id in plugin_config.repeater_group


@Rule
async def not_in_blacklist(raw_message: Message = EventMessage()) -> bool:
    return raw_message not in plugin_config.repeater_blacklist


@Rule
async def should_repeat(event: GroupMessageEvent, raw_message: Message = EventMessage()) -> bool:
    message: Message = _message_preprocess(raw_message)
    logger.debug(f'[复读姬] 这一次消息: {message}')
    logger.debug(f'[复读姬] 上一次消息: {last_message.get(event.group_id)}')
    if last_message.get(event.group_id) != message:
        message_times[event.group_id] = 1
    else:
        message_times[event.group_id] += 1
    logger.debug(f'[复读姬] 已重复次数: {message_times.get(event.group_id)}/{plugin_config.repeater_min_message_times}')
    last_message[event.group_id] = message
    return message_times.get(event.group_id) == plugin_config.repeater_min_message_times

repeat = on_message(rule=in_repeater_group & not_in_blacklist & should_repeat, priority=10, block=False)


@repeat.handle()
async def repeat_func(event: GroupMessageEvent, raw_message: Message = EventMessage()) -> None:
    logger.debug(f'[复读姬] 原始的消息: {str(event.message)}')
    logger.debug(f"[复读姬] 欲发送信息: {raw_message}")
    await repeat.finish(raw_message)
