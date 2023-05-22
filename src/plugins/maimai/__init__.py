from nonebot.typing import T_State
import asyncio
import json
import math
import re
from random import Random
from typing import Any

import aiofiles
from nonebot import MatcherGroup, get_driver, logger
from nonebot.adapters.onebot.v11 import (Bot, GroupMessageEvent, Message,
                                         MessageEvent, MessageSegment)
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.drivers import Driver
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventMessage, RegexGroup, EventPlainText
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from . import plate
from .best_pic import generate
from .consts import DIFFICULTY_NAME
from .image import get_cover_len4_id, image_to_bytesio, text_to_image
from .music import Chart, Mai, Music, MusicList
from .utils import get_random_inst, strftime
# from .guess import is_now_playing_guess_music, guesses, Guess
from .guess import Guess

driver: Driver = get_driver()
default_command_start: str = tuple(driver.config.command_start)[0]
help_str: str = f'''
欢迎使用BioBot的maimai模块！
本模块魔改自Diving-Fish/mai-bot和Yuri-YuzuChaN/maimaiDX
maimai模块可用命令如下：
· {default_command_start}help maimai  # 查看本帮助
· {default_command_start}(今日舞萌|今日mai)  # 查看今天的舞萌运势
· [...]maimai[...]什么  # 随机一首歌
· 随个[dx|sd|标准][绿|黄|红|紫|白]<难度>  # 随机一首指定条件的乐曲
· {default_command_start}(b40|b50)[<@某人>|<qq号>|<水鱼网昵称>]  # 查询自己或别人的b40/b50
· <牌子名称>进度  # 查询牌子进度
· {default_command_start}查歌 <乐曲标题的一部分>  # 通过标题查询乐曲
· [绿|黄|红|紫|白]id<乐曲编号>  # 通过id查询乐曲或谱面
· <乐曲别名>是什么歌  # 通过别名查询乐曲
· {default_command_start}(添加|删除)别名 <乐曲id> <乐曲别名>  # 添加/删除乐曲别名
· {default_command_start}查询别名 <乐曲id>  # 查询乐曲别名
· {default_command_start}定数查歌 <定数>  # 查询定数对应的乐曲
· {default_command_start}定数查歌 <定数下限> <定数上限>  # 查询定数对应的乐曲
· {default_command_start}分数线 (绿|黄|红|紫|白)<乐曲id> <分数线>  # 详情请输入“分数线 帮助”查看
'''.strip()

__plugin_meta__ = PluginMetadata(
    name='maimai',
    description='maimai查分/查歌/随机/查别名/查定数/查分数线',
    usage=help_str
)


@driver.on_startup
async def on_startup_func() -> None:
    '''bot启动时获取曲目信息和别名信息'''
    logger.info('正在获取乐曲信息...')
    await Mai.get_music()
    logger.info('正在获取别名信息...')
    await Mai.get_aliases()

maimai_command_group = MatcherGroup(priority=3, block=False)
help = maimai_command_group.on_command('help maimai')
today_maimai = maimai_command_group.on_command('今日舞萌', aliases={'今日mai', 'jrwm', '今日乌蒙'})
maimai_what = maimai_command_group.on_regex(r"maimai.*什么", flags=re.RegexFlag.IGNORECASE)
spec_rand = maimai_command_group.on_regex(
    r"[随来给]个(dx|sd|标准)?(绿|黄|红|紫|白)?(?:(\d{1,2}\.\d)|(\d{1,2}\+?))", flags=re.RegexFlag.IGNORECASE)
best_40 = maimai_command_group.on_command('b40', aliases={'best40'})
best_50 = maimai_command_group.on_command('b50', aliases={'best50'})
search_music_by_inner = maimai_command_group.on_command('定数查歌')
search_music_by_title = maimai_command_group.on_command('查歌')
search_music_by_alias = maimai_command_group.on_regex(r'(.*)(?:是什么歌|是啥歌)')
query_chart = maimai_command_group.on_regex(r"^(绿|黄|红|紫|白)?\s*id\s*(\d+)")
score_line = maimai_command_group.on_command('分数线')
add_alias = maimai_command_group.on_command('添加别名', aliases={'添加别称', '增加别名', '增加别称'})
delete_alias = maimai_command_group.on_command('删除别名', aliases={'删除别称'})
query_alias = maimai_command_group.on_command('查询别名')
# query_alias = maimai_command_group.on_regex(r'(.*)有什么别名')
plate_process = maimai_command_group.on_regex(
    r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞](?:[極极将神舞]|舞舞)|霸者)进度\s*(.*)')
guess_music_start = maimai_command_group.on_command('猜歌')
guess_music_solve = maimai_command_group.on_message()  # rule=is_now_playing_guess_music)


search_music_by_inner_help_str: str = '''
命令格式为
· 定数查歌 <定数>  # 查询定数对应的乐曲
· 定数查歌 <定数下限> <定数上限>  # 查询定数对应的乐曲
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
            (f'TOUCH: {chart.touch}\n' if chart.is_dx else '') +
            f'BREAK: {chart.break_}\n'
            f'谱师: {chart.charter}'
        )])


@help.handle()
async def help_func() -> None:
    await help.finish(MessageSegment.image(image_to_bytesio(text_to_image(help_str))))


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

    length_of_result: int = sum(len(music.diff) for music in result)
    if length_of_result <= 48:
        result.sort(key=lambda music: int(music.id))
        await search_music_by_inner.finish(f'查询到{length_of_result}首乐曲：\n'
                                           + '\n'.join(music_info_with_diff_compact(music, diff)
                                                       for music in result for diff in music.diff))
    await search_music_by_inner.finish(f"结果过多（{length_of_result} 条），请缩小查询范围。")


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
    try:
        id, alias = message.extract_plain_text().split()
    except ValueError:
        await add_alias.finish('命令格式：\n添加别名 <乐曲id> <乐曲别名>')
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
    await add_alias.finish(f'已为 {id}. {music.title} 添加别名“{alias}”')


@delete_alias.handle()
async def delete_alias_func(bot: Bot, event: GroupMessageEvent, message: Message = CommandArg()) -> None:
    try:
        id, alias = message.extract_plain_text().split()
    except ValueError:
        await add_alias.finish('命令格式：\n删除别名 <乐曲id> <乐曲别名>')
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
    await delete_alias.finish(f'已删除 {id}. {music.title} 的别名“{alias}”')


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


wm_list: list[str] = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']


@today_maimai.handle()
async def today_maimai_func(event: MessageEvent) -> None:
    random_inst: Random = get_random_inst(event.user_id)
    luck: int = random_inst.randint(0, 100)
    wm_value: list[int] = [random_inst.randrange(4) for _ in wm_list]
    lines: list[str] = []
    lines.append(f'今日人品值：{luck}')
    for i, (value, content) in enumerate(zip(wm_value, wm_list)):
        if value == 3:
            lines.append(f'宜 {content}')
        elif value == 0:
            lines.append(f'忌 {content}')
    lines.append('Bio提醒您：打机时不要大力拍打或滑动哦')
    lines.append('今日推荐歌曲：')
    music: Music = random_inst.choice(Mai.music_list)
    await today_maimai.finish(Message([MessageSegment.text('\n'.join(lines))]) + music_info(music))


@score_line.handle()
async def score_line_func(message: Message = CommandArg()):
    regex = r'(绿|黄|红|紫|白)(id)?([0-9]+)'
    argv: list[str] = message.extract_plain_text().strip().split()
    if len(argv) == 1 and argv[0] == '帮助':
        await score_line.send(MessageSegment.image(image_to_bytesio(text_to_image(query_score_help_str))))
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
            chart: Chart = music.charts[diff]
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
async def best_pic_func(event: MessageEvent, matcher: Matcher, message: Message = CommandArg()) -> None:
    if not message:  # b40
        payload = {'qq': event.user_id}
    else:
        specific_qq: int | None = get_at_qq(message)
        if specific_qq is None:  # b40 name
            username: str = message.extract_plain_text().strip()
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
        payload['version'] = list(set(version for version in list(plate.plate_to_version.values())[:-5]))
    else:
        payload['version'] = [plate.plate_to_version[version_han]]
    data = await plate.player_plate_data(payload, version_han, target_han, nickname)
    await plate_process.send(data)


@guess_music_start.handle()
async def guess_music_start_func(event: GroupMessageEvent, state: T_State) -> None:
    # if event.group_id not in guess.config['enable']:
    #     await guess_music_start.finish('该群已关闭猜歌功能，开启请输入 开启mai猜歌', reply_message=True)
    # if event.group_id in guesses:
    #     await guess_music_start.finish('该群已有正在进行的猜歌', reply_message=True)
    guess = Guess()
    # guesses[event.group_id] = guess
    state['guess'] = guess
    await guess_music_start.send(
        '我将从热门乐曲中选择一首歌，每隔8秒描述它的特征\n'
        '请输入乐曲的 id 或 标题 或 别名（不区分大小写）进行猜歌\n'
        'DX乐谱和标准乐谱视为两首歌\n'
        '猜歌时查歌等其他命令依然可用\n'
    )
    await guess_music_loop(event, state)


@guess_music_solve.handle()
async def guess_music_solve_func(event: GroupMessageEvent, state: T_State, message: str = EventPlainText()) -> None:
    message = message.strip()
    guess: Guess = state['guess']
    answer: Music = guess.music
    guess_musics: MusicList = Mai.music_list.by_alias(message)
    if len(guess_musics) == 1 and answer.id == guess_musics[0].id:
        guess.finished = True
        await guess_music_solve.finish('猜对了，答案是：' + music_info(answer), reply_message=True)


async def guess_music_loop(event: GroupMessageEvent, state: T_State) -> None:
    guess: Guess = state['guess']
    if guess.finished:
        return
    if guess.round == 0:
        await asyncio.sleep(5)
    else:
        await asyncio.sleep(10)
    if guess.round < guess.ROUNDS:
        await guess_music_start.send(guess.give_hint())
    if guess.round == guess.ROUNDS:
        await give_answer(event, state)
    await guess_music_loop(event, state)


async def give_answer(event: GroupMessageEvent, state: T_State) -> None:
    await asyncio.sleep(30)
    guess: Guess = state['guess']
    if guess.finished:
        return
    guess.finished = True
    await guess_music_solve.finish('答案是：' + music_info(guess.music), reply_message=True)
