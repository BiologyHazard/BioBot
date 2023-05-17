from typing import NoReturn

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Bot, Message, MessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg, CommandStart, EventToMe
from nonebot.plugin import PluginMetadata

from .theory import Theory, Tile

__plugin_meta__ = PluginMetadata(
    name='麻将牌理分析',
    description='',
    usage=(
        ''
    )
)


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me

向听: type[Matcher] = on_command('向听数', aliases={'向听'}, rule=with_command_start_or_to_me, priority=5)
何切: type[Matcher] = on_command('何切', aliases={'牌理', '牌理分析'}, rule=with_command_start_or_to_me, priority=5)


@向听.handle()
async def 向听_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> NoReturn:
    try:
        theory: Theory = Theory(str(message).strip())
    except ValueError:
        await 向听.finish(f'无法解析命令参数')

    if theory.tiles.total() > 14:
        await 向听.finish('最多可以计算14张牌')
    if theory.tiles.total() % 3 != 2:
        await 向听.finish('3n+1张牌的计算正在锐意开发中')

    await 向听.finish(f'{theory.tiles_with_dora}的向听数是{theory.向听数()}')


@何切.handle()
async def 何切_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> NoReturn:
    try:
        theory: Theory = Theory(str(message).strip())
    except ValueError:
        await 何切.finish(f'无法解析命令参数')

    if theory.tiles.total() > 14:
        await 何切.finish('最多可以计算14张牌')
    if theory.tiles.total() % 3 != 2:
        await 何切.finish('3n+1张牌的计算正在锐意开发中')

    ans: list[tuple[int, list[int]]] = theory.何切()
    output: list[str] = [f'{theory.tiles_with_dora}的切牌选择是']
    for i, (qiepai, jinzhang) in enumerate(ans):
        output.append(f"{i+1}. 切{Tile(qiepai)}, 摸{', '.join(str(Tile(i)) for i in jinzhang)}")
    await 何切.finish('\n'.join(output))
