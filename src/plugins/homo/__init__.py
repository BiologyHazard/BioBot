from typing import NoReturn

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg, CommandStart, EventToMe
from nonebot.plugin import PluginMetadata

from .homo import generate_homo

__plugin_meta__ = PluginMetadata(
    name='恶臭论证',
    description='',
    usage=(
        ''
    )
)


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me

generate: type[Matcher] = on_command('恶臭',
                                     aliases={'恶臭论证', 'homo', '114514'},
                                     rule=with_command_start_or_to_me,
                                     priority=5)


@generate.handle()
async def homo_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> NoReturn:
    await generate.finish(generate_homo(str(message)))
