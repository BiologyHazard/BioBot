from typing import NoReturn

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg, CommandStart, EventToMe

from .theory import Theory


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me

shanten: type[Matcher] = on_command('向听数',
                                    aliases={'向听'},
                                    rule=with_command_start_or_to_me,
                                    priority=5)

heqie: type[Matcher] = on_command('何切',
                                  aliases={'牌理', '牌理分析'},
                                  rule=with_command_start_or_to_me,
                                  priority=5)


@shanten.handle()
async def shanten_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()):
    # await generate.finish(generate_homo(str(message)))
    try:
        theory: Theory = Theory(str(message).strip())
        await shanten.send(f'{theory.tiles_with_dora}的向听数是{theory.shanten()}')
    except Exception:
        await shanten.send(f'出现未知错误')


@heqie.handle()
async def heqie_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()):
    # await generate.finish(generate_homo(str(message)))
    try:
        theory: Theory = Theory(str(message).strip())
        await shanten.send(f'{theory.tiles_with_dora}的切牌选择是\n{theory.何切()}')
    except Exception:
        await shanten.send(f'出现未知错误')
