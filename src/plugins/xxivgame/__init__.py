from collections import defaultdict
from typing import Final, NoReturn

from nonebot import MatcherGroup, on_message
from nonebot.adapters.onebot.v11 import (GroupMessageEvent, Message,
                                         MessageEvent, PrivateMessageEvent)
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, CommandStart, EventPlainText, EventToMe
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .expression import replace_dict
from .xxivcalculator import Expression, XXIVSolver

__plugin_meta__ = PluginMetadata(
    name='24点游戏',
    description='不止24点，可自定义最终要计算的数/数字个数/有解概率',
    usage=(
        '· #24点 [<数字个数>] [<最终要计算的数>]  # 让bot随机出一道题\n'
        '· #24点 <最终要计算的数> <若干个数作为题目>  # 让bot解题，使用例：#24点 24 3 3 7 7 --> "7 × (3 + 3 ÷ 7)"\n'
        '· #有解概率 <有解概率>  # 改变有解概率\n'
    )
)

MAX_LENGTH: Final[int] = 64
DEFAULT_SOLVABLE_PROBABILITY: Final[float] = 1.0

last_solution: dict[str, Expression | None] = dict()
solvable_probability: defaultdict[str, float] = defaultdict(lambda: DEFAULT_SOLVABLE_PROBABILITY)


def event_to_dict_key(event: MessageEvent) -> str:
    if isinstance(event, GroupMessageEvent):
        return f'group_{event.group_id}'
    elif isinstance(event, PrivateMessageEvent):
        return f'private_{event.user_id}'
    else:
        raise TypeError


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me


@Rule
async def is_valid_expression(message: str = EventPlainText()) -> bool:
    if len(message) > MAX_LENGTH:
        return False

    for k, v in replace_dict.items():
        message = message.replace(k, v)

    if not all(char in '0123456789()+-*/' for char in message):
        return False

    if ('**' in message) or ('//' in message):
        # 如果有**或//，则忽略
        return False

    if all(operator not in message.lstrip('+-') for operator in '+-*/'):
        # 如果message是（带符号或括号的）纯数字，没有二元运算符，则忽略
        return False

    return True


xxivgame_group = MatcherGroup(rule=with_command_start_or_to_me, priority=5)
start_game: type[Matcher] = xxivgame_group.on_command('24点')
look_answer: type[Matcher] = xxivgame_group.on_command('查看答案')
set_solvable_probability: type[Matcher] = xxivgame_group.on_command('有解概率')
check_answer: type[Matcher] = on_message(rule=is_valid_expression, priority=15)


@start_game.handle()
async def start_game_func(event: MessageEvent, message: Message = CommandArg()) -> NoReturn:
    try:
        parameters: list[str] = message.extract_plain_text().split()
        if len(parameters) >= 3:
            target = int(parameters[0])
            nums: list[int] = [int(para) for para in parameters[1:]]
            solution: Expression | None = XXIVSolver(target, nums).solve()
            if solution is None:
                await start_game.finish('无解')
            await start_game.finish(str(solution))
        n: int = 4
        target: int = 24
        if len(parameters) == 1:
            n = int(parameters[0])
        elif len(parameters) == 2:
            n, target = int(parameters[0]), int(parameters[1])

    except ValueError:
        await start_game.finish('无法解析命令参数喵~')

    if n > 8:
        await start_game.finish('数字太多了，不想出题喵~')
    if target > 128:
        await start_game.finish('数字太大了，不想出题喵~')

    max_trials: int | None = 8
    problem, solution = XXIVSolver.generate(
        n=n,
        target=target,
        solvable_probability=solvable_probability[event_to_dict_key(event)],
        max_trials=max_trials)
    if problem is None:
        await start_game.finish(f'非常抱歉，尝试了{max_trials}次后未找到有解的题目。')

    last_solution[event_to_dict_key(event)] = solution
    await start_game.finish(f'用四则运算计算{target}\n' + '   '.join(str(x) for x in problem))


@look_answer.handle()
async def look_answer_func(event: MessageEvent) -> NoReturn:
    if event_to_dict_key(event) not in last_solution:
        await look_answer.finish('当前没有题目，发送“#24点”生成题目。')

    solution: Expression | None = last_solution[event_to_dict_key(event)]
    if solution is None:
        await start_game.finish('无解')
    await look_answer.finish(f'{str(solution)} = {solution.value}')


@check_answer.handle()
async def check_answer_func(message: str = EventPlainText()) -> None:
    try:
        result: float = round(eval(message, {}, {}), 2)
    except SyntaxError:
        return
    except ZeroDivisionError:
        await check_answer.finish('除数不能为0')
    else:
        message = message.replace('+', ' + ').replace('-', ' - ').replace('*', ' × ').replace('/', ' ÷ ')
        await check_answer.finish(f'{message} = {result}')


@set_solvable_probability.handle()
async def set_solvable_probability_func(event: MessageEvent, message: Message = CommandArg()) -> NoReturn:
    try:
        probability: float = float(str(message).strip())
    except ValueError:
        await set_solvable_probability.finish('无法解析命令参数喵~')

    if 0 <= probability <= 1:
        solvable_probability[event_to_dict_key(event)] = probability
        await set_solvable_probability.finish(f'有解概率已经调整为{probability}')
    else:
        await set_solvable_probability.finish('概率必须在0~1之间')
