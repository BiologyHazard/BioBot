import datetime

from nonebot import get_driver, on_fullmatch, on_regex
from nonebot.adapters.onebot.v11 import GroupMessageEvent
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import RegexGroup
from nonebot.plugin import PluginMetadata

from .config import data_path
from .tygj import Tygj, strftime, strftimedelta

__plugin_meta__ = PluginMetadata(
    name='tygj',
    description='',
    usage='tygj？tyg114514'
)

tyg_query: type[Matcher] = on_fullmatch('tygj')
tyg_change: type[Matcher] = on_regex(r'^tyg([-+]?)(\d{1,16})$')


driver: Driver = get_driver()


@driver.on_startup
async def on_startup_func() -> None:
    global inst
    inst = Tygj.load_from_file(data_path)


@tyg_query.handle()
async def tyg_query_func(event: GroupMessageEvent) -> None:
    if not Tygj.in_business_hours(event.time):
        await tyg_query.finish('tyg闭店中')

    global inst
    if inst is None or datetime.date.fromtimestamp(event.time) != datetime.date.fromtimestamp(inst.time):
        inst = None
        await tyg_query.finish(f'我不到啊，问群友罢（')

    await tyg_query.finish(f"tyg{inst.num}\n# 由{inst.card or inst.nickname} "
                           f"({inst.qqid}) 于{strftime(inst.time)} ({strftimedelta(inst.time, event.time)}前)设置")


@tyg_change.handle()
async def tyg_change_func(event: GroupMessageEvent, group: tuple[str, str] = RegexGroup()) -> None:
    if not Tygj.in_business_hours(event.time):
        await tyg_query.finish('tyg闭店中')

    global inst
    if inst is None or datetime.date.fromtimestamp(event.time) != datetime.date.fromtimestamp(inst.time):
        tyg_num: int = 0
    else:
        tyg_num = inst.num

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
    inst = Tygj(
        num=tyg_num,
        qqid=event.sender.user_id,
        nickname=event.sender.nickname,
        card=event.sender.card,
        role=event.sender.role,
        time=event.time
    )
    inst.save_to_file(data_path)
    await tyg_change.finish(f'tyg人数已从{tyg_num_old}更改为{tyg_num}')
