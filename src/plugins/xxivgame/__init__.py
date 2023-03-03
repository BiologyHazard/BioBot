import time

from nonebot import on_command
from nonebot.adapters.onebot.v11 import Message
from nonebot.internal.matcher import Matcher
from nonebot.internal.rule import Rule
from nonebot.params import CommandArg, CommandStart, EventToMe

from .xxivcalculator import XXIV_Solver


@Rule
async def with_command_start_or_to_me(command_start: str = CommandStart(), to_me: bool = EventToMe()) -> bool:
    return bool(command_start) or to_me

start_game: type[Matcher] = on_command('24点', rule=with_command_start_or_to_me, priority=5)


@start_game.handle()
async def roll_func(message: Message = CommandArg()) -> None:
    try:
        parameters: list[str] = str(message).split()
        if len(parameters) >= 3:
            target = int(parameters[0])
            nums: list[int] = list(map(int, parameters[1:]))
            await start_game.finish(XXIV_Solver(target, False).solve_with_record(nums=nums)[1])
        n: int = 4
        target: int = 24
        if len(parameters) == 1:
            n = int(parameters[0])
        elif len(parameters) == 2:
            n, target = int(parameters[0]), int(parameters[0])

        # await start_game.finish(XXIV_Solver.generate(n=n, target=target, solvable=True))

    except Exception:
        return
