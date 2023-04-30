from nonebot import on_regex, on_fullmatch
from nonebot.matcher import Matcher
from nonebot.params import RegexGroup

tyg_num: int = 0
tyg_query: type[Matcher] = on_fullmatch('tygj')
tyg_change: type[Matcher] = on_regex(r'^tyg([-+]?)(\d{1,16})$')


@tyg_query.handle()
async def tyg_query_func() -> None:
    await tyg_query.finish(f'tyg{tyg_num}')


@tyg_change.handle()
async def tyg_change_func(group: tuple[str, str] = RegexGroup()) -> None:
    global tyg_num
    tyg_num_old: int = tyg_num
    signature: str = group[0]
    num_change: int = int(group[1])
    if not signature:
        tyg_num = num_change
    elif signature == '+':
        tyg_num += num_change
    elif signature == '-':
        if tyg_num - num_change < 0:
            await tyg_change.finish(f'tyg的人数不能小于0')
        tyg_num -= num_change
    await tyg_change.finish(f'tyg人数已从{tyg_num_old}更改为{tyg_num}')
