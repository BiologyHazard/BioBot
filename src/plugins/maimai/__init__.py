import math
import re
from typing import Any, Literal
import aiofiles
import json

from nonebot import MatcherGroup, get_driver, logger
from nonebot.adapters.onebot.v11 import (Bot, Event, GroupMessageEvent,
                                         Message, MessageEvent, MessageSegment)
from nonebot.permission import SUPERUSER
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.drivers import Driver
from nonebot.params import CommandArg, EventMessage, RegexGroup
from nonebot.matcher import Matcher

from . import maimaidx_plate
from .image import text_to_image_base64_str, image_to_bytesio
from .best_pic import generate
from .maimai_consts import DIFFICULTY_NAME
from .maimai_music import Chart, Mai, Music, MusicList, get_cover_len4_id
from .utils import get_hash_value, strftime

driver: Driver = get_driver()


@driver.on_startup
async def on_startup_func() -> None:
    '''
    bot启动时开始获取所有数据
    '''
    await Mai.get_music()
    await Mai.get_aliases()

maimai_command_group = MatcherGroup(priority=3, block=False)
help = maimai_command_group.on_command('help maimai')
today_maimai = maimai_command_group.on_command('今日舞萌', aliases={'今日mai', 'jrwm', '今日乌蒙'})
search_music_by_inner = maimai_command_group.on_command('定数查歌')
search_music_by_title = maimai_command_group.on_command('查歌')
search_music_by_alias = maimai_command_group.on_regex(r'(.*)(?:是什么歌|是啥歌)')
spec_rand = maimai_command_group.on_regex(
    r"[随来给]个(dx|sd|标准)?(绿|黄|红|紫|白)?(?:(\d{1,2}\.\d)|(\d{1,2}\+?))", flags=re.RegexFlag.IGNORECASE)
maimai_what = maimai_command_group.on_regex(r"maimai.*什么", flags=re.RegexFlag.IGNORECASE)
query_chart = maimai_command_group.on_regex(r"^(绿|黄|红|紫|白)?\s*id\s*(\d+)")
score_line = maimai_command_group.on_command('分数线')
best_40 = maimai_command_group.on_command('b40', aliases={'best40'})
best_50 = maimai_command_group.on_command('b50', aliases={'best50'})
add_alias = maimai_command_group.on_command('添加别名', aliases={'添加别称', '增加别名', '增加别称'})
delete_alias = maimai_command_group.on_command('删除别名', aliases={'删除别称'})
query_alias = maimai_command_group.on_command('查询别名')
query_alias = maimai_command_group.on_regex('查询别名')
plate_process = maimai_command_group.on_regex(
    r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞](?:[極极将神舞]|舞舞)|霸者)进度\s*(.*)')

help_str: str = '''
欢迎使用BioBot的maimai模块！
本模块魔改自Diving-Fish/mai-bot
maimai模块可用命令如下：
· (今日舞萌|今日mai)  # 查看今天的舞萌运势
· (b40|b50)[<@某人>|<qq号>|<水鱼网昵称>]  # 查询自己或别人的b40/b50
· [...]maimai[...]什么  # 随机一首歌
· 随个[dx|sd|标准][绿|黄|红|紫|白]<难度>  # 随机一首指定条件的乐曲
· 查歌 <乐曲标题的一部分>  # 通过标题查询乐曲
· [绿|黄|红|紫|白]id<乐曲编号>  # 通过查询乐曲或谱面
· <乐曲别名>是什么歌  # 查询乐曲别名对应的乐曲
· (添加|删除)别名 <乐曲id> <乐曲别名>  # 添加/删除乐曲别名
· 查询别名 <乐曲id>  # 查询乐曲别名
· 定数查歌 <定数>  # 查询定数对应的乐曲
· 定数查歌 <定数下限> <定数上限>  # 查询定数对应的乐曲
· 分数线 (绿|黄|红|紫|白)<乐曲id> <分数线>  # 详情请输入“分数线 帮助”查看
'''.strip()

search_music_by_inner_help_str: str = '''
命令格式为
1. 定数查歌 <定数>
2. 定数查歌 <定数下限> <定数上限>
'''.strip()

query_score_help_str: str = '''
此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>
例如：分数线 紫799 100
命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落 等价的 TAP GREAT 数。
以下为 TAP GREAT 的对应表：
GREAT/GOOD/MISS
TAP     1/2.5/5
HOLD    2/5/10
SLIDE   3/7.5/15
TOUCH   1/2.5/5
BREAK   5/12.5/25(外加200落)
'''.strip()


def get_at_qq(message: Message) -> int | None:
    for message_segment in message:
        if message_segment.type == 'at' and message_segment.data['qq'] != 'all':
            return int(message_segment.data['qq'])


def music_info(music: Music) -> Message:
    return Message([
        MessageSegment.image(f'https://www.diving-fish.com/covers/{get_cover_len4_id(music.id)}.png'),
        MessageSegment.text(f'{music.id}. {music.title}\n'
                            f'艺术家：{music.artist}\n'
                            f'分类：{music.genre}\n'
                            f'速度：{music.bpm}bpm\n'
                            f'版本：{music.version}\n'
                            f'等级：{" / ".join(music.level)}\n'
                            f'定数：{" / ".join(map(str, music.ds))}')])


def music_info_compact(music: Music) -> str:
    return f'{music.id}. {music.title}'


def music_info_with_diff_compact(music: Music, diff: int) -> str:
    return f'{music.id}. {music.title} {DIFFICULTY_NAME[diff]} {music.level[diff]} ({music.ds[diff]})'


def chart_info(music: Music, diff_index: int) -> Message:
    chart: Chart = music.charts[diff_index]
    ds: float = music.ds[diff_index]
    level: str = music.level[diff_index]
    return Message([
        MessageSegment.image(f'https://www.diving-fish.com/covers/{get_cover_len4_id(music.id)}.png'),
        MessageSegment.text(
            f'{music.id}. {music.title} {DIFFICULTY_NAME[diff_index]} {level} ({ds})\n'
            f'艺术家：{music.artist}\n'
            f'分类：{music.genre}\n'
            f'速度：{music.bpm} bpm\n'
            f'版本：{music.version}\n'
            f'TAP: {chart.tap}\n'
            f'HOLD: {chart.hold}\n'
            f'SLIDE: {chart.slide}\n' +
            f'TOUCH: {chart.touch}\n' if len(chart['notes']) == 4 else '' +
            f'BREAK: {chart.break_}\n'
            f'谱师: {chart.charter}'
        )])


@help.handle()
async def help_func() -> None:
    await help.finish(MessageSegment.image(text_to_image_base64_str(help_str)))


@search_music_by_inner.handle()
async def search_music_by_inner_func(message: Message = CommandArg()):
    argv: list[str] = str(message).strip().split()
    try:
        if len(argv) == 1:
            ds = float(argv[0])
            assert math.isfinite(ds), ValueError
        elif len(argv) == 2:
            ds = (float(argv[0]), float(argv[1]))
            assert math.isfinite(ds[0]) and math.isfinite(ds[1]), ValueError
        else:
            raise ValueError
    except ValueError:
        await search_music_by_inner.finish(search_music_by_inner_help_str)

    result: MusicList = Mai.music_list.filter(ds=ds)
    if not result:
        await search_music_by_inner.finish('没有找到这样的乐曲。')
    if len(result) <= 48:
        # len(result) 并不是结果的数量，待修改
        result.sort(key=lambda music: int(music.id))
        await search_music_by_inner.finish(f'查询到{len(result)}首乐曲：\n'
                                           + '\n'.join(music_info_with_diff_compact(music, diff)
                                                       for music in result for diff in music.diff))
    await search_music_by_inner.finish(f"结果过多（{len(result)} 条），请缩小查询范围。")


@search_music_by_title.handle()
async def search_music_by_title_func(message: Message = CommandArg()) -> None:
    name: str = message.extract_plain_text()
    if not name:
        await search_music_by_title.finish('请输入要查询的歌曲。')
    result: MusicList = Mai.music_list.filter(title_search=name)
    if not result:
        await search_music_by_title.finish('没有找到这样的乐曲。')
    if len(result) == 1:
        (music, ) = result
        await search_music_by_title.finish(music_info(music))
    if len(result) <= 48:
        result.sort(key=lambda music: int(music.id))
        await search_music_by_title.finish(f'查询到{len(result)}首乐曲：\n'
                                           + '\n'.join(music_info_compact(music) for music in result))
    await search_music_by_title.finish(f"结果过多（{len(result)}条），请缩小查询范围。")


@search_music_by_alias.handle()
async def search_music_by_alias_func(group: tuple[str] = RegexGroup()):
    (alias, ) = group
    result: MusicList = Mai.music_list.by_alias(alias)
    if not result:
        await search_music_by_alias.finish('没有找到这样的乐曲。')
    if len(result) == 1:
        (music, ) = result
        await search_music_by_alias.finish(music_info(music))
    if len(result) <= 48:
        await search_music_by_alias.finish(f'查询到{len(result)}首乐曲：\n'
                                           + '\n'.join(music_info_compact(music) for music in result))
    await search_music_by_alias.finish(f'结果过多（{len(result)}条），请缩小查询范围。')


@add_alias.handle()
async def add_alias_func(event: GroupMessageEvent, message: Message = CommandArg()) -> None:
    id, alias = message.extract_plain_text().split()
    music: Music | None = Mai.music_list.by_id(id)
    if music is None:
        await add_alias.finish(f'没有id为{id}的乐曲。')
    if alias.lower() in (x.lower() for x in music.aliases):
        await add_alias.finish(f'该别名已存在。')
    info: dict[str, int | str | None] = {'group': event.group_id,
                                         'qqid': event.user_id,
                                         'nickname': event.sender.nickname,
                                         'card': event.sender.card,
                                         'role': event.sender.role,
                                         'time': event.time, }
    music.aliases[alias] = info
    async with aiofiles.open('data/maimai/aliases.json', 'r', encoding='utf-8') as fp:
        aliases = json.loads(await fp.read())
    if id not in aliases:
        aliases[id] = {'title': music.title, 'aliases': {}}
    aliases[id]['aliases'][alias] = info
    async with aiofiles.open('data/maimai/aliases.json', 'w', encoding='utf-8') as fp:
        await fp.write(json.dumps(aliases, ensure_ascii=False, indent=4))
    await add_alias.finish('别名添加成功。')


@delete_alias.handle()
async def delete_alias_func(bot: Bot, event: GroupMessageEvent, message: Message = CommandArg()) -> None:
    id, alias = message.extract_plain_text().split()
    music: Music | None = Mai.music_list.by_id(id)
    if music is None:
        await delete_alias.finish(f'没有id为{id}的乐曲。')
    if alias not in music.aliases:
        await delete_alias.finish(f'该别名不存在。')
    if music.aliases[alias]['group'] != event.group_id:
        await delete_alias.finish(f'别名“{alias}”由非本群的成员添加，不可在本群删除。')
    if (music.aliases[alias]['role'] in ('owner', 'admin')
            and not await (SUPERUSER | GROUP_OWNER | GROUP_ADMIN)(bot, event)):
        await delete_alias.finish(f'别名“{alias}”由群管理员添加，只可由群管理员删除。')

    del music.aliases[alias]
    async with aiofiles.open('data/maimai/aliases.json', 'r', encoding='utf-8') as fp:
        aliases = json.loads(await fp.read())
    del aliases[id]['aliases'][alias]
    async with aiofiles.open('data/maimai/aliases.json', 'w', encoding='utf-8') as fp:
        await fp.write(json.dumps(aliases, ensure_ascii=False, indent=4))
    await delete_alias.finish('别名删除成功。')


@query_alias.handle()
async def query_alias_func(event: GroupMessageEvent, message: Message = CommandArg()) -> None:
    id: str = message.extract_plain_text()
    music: Music | None = Mai.music_list.by_id(id)
    if music is None:
        await query_alias.finish(f'没有id为{id}的乐曲。')
    if not music.aliases:
        await query_alias.finish(f'{id}. {music.title}暂无别名。')
    result: list[str] = [f'{id}. {music.title}的别名共{len(music.aliases)}个：']
    for i, (alias, info) in enumerate(music.aliases.items()):
        # if info['group'] != event.group_id:
        #     info_str: str = f'{info["card"] or info["nickname"]} ({info["qqid"]})'
        # else:
        #     info_str = '非本群的成员'
        result.append(f'{i+1}. {alias}  # 由{info["card"] or info["nickname"]} ({info["qqid"]}) 于{strftime(info["time"])}设置')
    await query_alias.finish('\n'.join(result))


@spec_rand.handle()
async def spec_rand_func(group: tuple[str | None, str | None, str | None, str | None] = RegexGroup()) -> None:
    music_type, diff, ds, level = group
    if ds is not None:
        ds = float(ds)
    if music_type is not None:
        if music_type.lower() == "dx":
            music_type = "DX"
        elif music_type.lower() == "sd" or group[0] == "标准":
            music_type = "SD"
    if diff is None:
        diff_index = None
    else:
        diff_index = ['绿黄红紫白'.index(diff)]
    music_data: MusicList = Mai.music_list.filter(level=level, ds=ds, diff=diff_index, type_=music_type)
    if len(music_data) == 0:
        await spec_rand.finish("没有这样的乐曲哦。")
    else:
        await spec_rand.finish(music_info(music_data.random()))


@maimai_what.handle()
async def maimai_what_func() -> None:
    await maimai_what.finish(music_info(Mai.music_list.random()))


@query_chart.handle()
async def query_chart_func(group: tuple[str | None, str] = RegexGroup()):
    music_id: str = group[1]
    music: Music | None = Mai.music_list.by_id(music_id)
    if music is None:
        await query_chart.finish('未找到该乐曲。')
    if group[0] is not None:
        level_index: int = '绿黄红紫白'.index(group[0])
        await query_chart.finish(chart_info(music, level_index))
    else:
        await query_chart.finish(music_info(music))


wm_list: list[str] = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']


@today_maimai.handle()
async def today_maimai_func(event: MessageEvent, message: Message = CommandArg()):
    qq: int = event.user_id
    hash_value: int = get_hash_value(qq)
    luck: int = hash_value % 101
    wm_value: list[int] = [(hash_value >> (i*2)) & 3 for i in range(len(wm_list))]
    lines: list[str] = []
    lines.append(f'今日人品值：{luck}')
    for i, (value, content) in enumerate(zip(wm_value, wm_list)):
        if value == 3:
            lines.append(f'宜 {content}')
        elif value == 0:
            lines.append(f'忌 {content}')
    lines.append('Bio提醒您：打机时不要大力拍打或滑动哦')
    lines.append('今日推荐歌曲：')
    music: Music = Mai.music_list[hash_value % len(Mai.music_list)]
    await today_maimai.finish(Message([MessageSegment.text('\n'.join(lines))]) + music_info(music))


@score_line.handle()
async def score_line_func(message: Message = CommandArg()):
    regex = r'(绿|黄|红|紫|白)(id)?([0-9]+)'
    argv: list[str] = message.extract_plain_text().strip().split()
    if len(argv) == 1 and argv[0] == '帮助':
        await score_line.send(MessageSegment.image(text_to_image_base64_str(query_score_help_str)))
    elif len(argv) == 2:
        try:
            match = re.match(regex, argv[0], flags=re.RegexFlag.IGNORECASE)
            if match is None:
                raise ValueError
            group = match.groups()
            diff: int = '绿黄红紫白'.index(group[0])
            chart_id: str = group[2]
            line = float(argv[1])
            if not math.isfinite(line):
                raise ValueError
            music: Music | None = Mai.music_list.by_id(chart_id)
            if music is None:
                raise ValueError
            chart: dict = music.charts[diff]
            tap: int = chart.tap
            slide: int = chart.slide
            hold: int = chart.hold
            touch: int = chart.touch
            break_: int = chart.break_
            total_score: int = 500 * tap + slide * 1500 + hold * 1000 + touch * 500 + break_ * 2500
            break_bonus: float = 0.01 / break_
            break_50_reduce: float = total_score * break_bonus / 4
            reduce: float = 101.0 - line
            if reduce < 0 or reduce > 101:
                raise ValueError
            await query_chart.finish(music_info_with_diff_compact(music, diff) +
                                     f'分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),\n'
                                     f'BREAK 50落(一共{break_}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)')
        except (ValueError, IndexError):
            await query_chart.finish("格式错误，输入“分数线 帮助”以查看帮助信息")


@best_40.handle()
@best_50.handle()
async def best_pic_func(event: MessageEvent, matcher: Matcher, arg: Message = CommandArg()) -> None:

    if not arg:  # b40
        payload = {'qq': event.user_id}
    else:
        specific_qq: int | None = get_at_qq(arg)
        if specific_qq is None:  # b40 name
            username: str = arg.extract_plain_text().strip()
            if username.isdigit():
                payload: dict[str, Any] = {'qq': int(username)}
            else:
                payload = {'username': username}
        else:  # b40 @xxxx
            payload = {'qq': specific_qq}

    if type(matcher) is best_50:
        payload['b50'] = True

    result = await generate(payload)
    if isinstance(result, str):
        await matcher.finish(result)
    await matcher.finish(MessageSegment.image(image_to_bytesio(result)))


@plate_process.handle()
async def plate_process_func(bot: Bot, event: MessageEvent, message: Message = EventMessage(), group: tuple[str, str] = RegexGroup()) -> None:
    plate_name_han, nickname = group
    version_han, target_han = plate_name_han[0], plate_name_han[1]

    if plate_name_han == '真将':
        await plate_process.finish('真系没有真将哦~')

    payload = dict()
    qqid: str = event.get_user_id()
    for message_segment in message:
        if message_segment.type == 'at' and message_segment.data['qq'] != 'all':
            qqid = message_segment.data['qq']
            payload['qq'] = qqid
            break

    if nickname and nickname.isdigit():
        qqid = nickname
        payload['qq'] = qqid
    else:
        payload['qq'] = qqid
    if 'qq' not in payload:
        payload['username'] = nickname

    if qqid != event.get_user_id():
        nickname = (await bot.get_stranger_info(user_id=int(qqid)))['nickname']

    if version_han in {'霸', '舞'}:
        payload['version'] = list(set(version for version in list(maimaidx_plate.plate_to_version.values())[:-5]))
    else:
        payload['version'] = [maimaidx_plate.plate_to_version[version_han]]
    data = await maimaidx_plate.player_plate_data(payload, version_han, target_han, nickname)
    await plate_process.send(data)
