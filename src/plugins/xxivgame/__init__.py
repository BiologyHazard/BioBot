from nonebot import on_command, on_message
from nonebot.adapters.onebot.v11 import Message, Bot, GroupMessageEvent
from nonebot.internal.matcher import Matcher
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg, CommandStart, EventToMe, EventMessage
from typing import NoReturn, Final

from .xxivcalculator import XXIVSolver, Expression
from .expression import replace_dict

last_problem: dict[int, list[int]] = dict()
last_solution: dict[int, Expression] = dict()


MAX_LENGTH: Final[int] = 64


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me

start_game: type[Matcher] = on_command('24点', rule=with_command_start_or_to_me, priority=5)
look_answer: type[Matcher] = on_command('查看答案', rule=with_command_start_or_to_me, priority=5)
check_answer: type[Matcher] = on_message(priority=15)


@start_game.handle()
async def start_game_func(bot: Bot, event: GroupMessageEvent, message: Message = CommandArg()) -> NoReturn:
    try:
        parameters: list[str] = str(message).split()
        if len(parameters) >= 3:
            target = int(parameters[0])
            nums: list[int] = [int(para) for para in parameters[1:]]
            await start_game.finish(str(XXIVSolver(target, nums).solve()))
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
    problem, solution = XXIVSolver.generate(n=n, target=target, ensure_solvable=True, max_trials=max_trials)
    if (problem is None) or (solution is None):
        await start_game.finish(f'非常抱歉，尝试了{max_trials}次后未找到有解的题目。')

    last_problem[event.group_id], last_solution[event.group_id] = problem, solution
    await start_game.finish(f'用四则运算计算{target}\n' + '   '.join(str(x) for x in problem))


@look_answer.handle()
async def look_answer_func(bot: Bot, event: GroupMessageEvent, message: Message = CommandArg()) -> NoReturn:
    if event.group_id not in last_solution:
        await look_answer.finish('当前没有题目，发送“#24点”生成题目。')

    await look_answer.finish(f'{str(last_solution[event.group_id])} = {last_solution[event.group_id].value}')


@check_answer.handle()
async def check_answer_func(bot: Bot, event: GroupMessageEvent, raw_message: Message = EventMessage()) -> None:
    # if event.group_id not in last_solution:
    #     return

    message: str = str(raw_message)
    if len(message) > MAX_LENGTH:
        return

    for k, v in replace_dict.items():
        message = message.replace(k, v)
    if all(char in '0123456789()+-*/' for char in message):
        if message.find('**') == -1 and message.find('//') == -1:
            try:
                result: float = round(eval(message, {}, {}), 1)
            except (SyntaxError, ZeroDivisionError):
                return
            else:
                message = message.replace('+', ' + ').replace('-', ' - ').replace('*', ' × ').replace('/', ' ÷ ')
                await check_answer.finish(f'{message} = {result}')
