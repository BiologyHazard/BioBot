import re
import math
from typing import Any, Literal

from nonebot import MatcherGroup, get_driver, logger
from nonebot.adapters.onebot.v11 import (Bot, Event, Message, MessageEvent,
                                         MessageSegment)
from nonebot.drivers import Driver
from nonebot.params import CommandArg, EventMessage, RegexGroup

from . import maimaidx_plate
from .image import image_to_base64, text_to_image, text_to_image_base64_str
from .maimai_best_40 import generate
from .maimai_best_50 import generate50
from .maimai_music import (Chart, Mai, Music, MusicList, get_cover_len4_id)
from .maimai_consts import DIFFICULTY_NAME
from .utils import get_hash_value

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
today_maimai = maimai_command_group.on_command('今日舞萌', aliases={'今日mai', 'jrwm'})
search_music_by_inner = maimai_command_group.on_command('定数查歌')
search_music_by_title = maimai_command_group.on_command('查歌')
search_music_by_alias = maimai_command_group.on_regex(r'(.*)是什么歌')
spec_rand = maimai_command_group.on_regex(
    r"随个(dx|sd|标准)?(绿|黄|红|紫|白)?(\d+\+?)", flags=re.RegexFlag.IGNORECASE)
maimai_what = maimai_command_group.on_regex(r"maimai.*什么", flags=re.RegexFlag.IGNORECASE)
query_chart = maimai_command_group.on_regex(r"^(绿|黄|红|紫|白)?id(\d+)")
query_score = maimai_command_group.on_command('分数线')
best_40_pic = maimai_command_group.on_command('b40')
best_50_pic = maimai_command_group.on_command('b50')
add_alias = maimai_command_group.on_command('添加别名')
delete_alias = maimai_command_group.on_command('删除别名')
plate_process_regex = r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸])([極极将舞神者]舞?)进度\s?(.+)?'
plate_process = maimai_command_group.on_regex(plate_process_regex)

help_str: str = '''
可用命令如下：
今日舞萌|今日mai  # 查看今天的舞萌运势
(b40|b50)[@某人|qq号|水鱼网昵称]  # 查询自己或别人的b40/b50
[...]maimai[...]什么  # 随机一首歌
随个[dx|sd|标准][绿|黄|红|紫|白]<难度>  # 随机一首指定条件的乐曲
查歌 <乐曲标题的一部分>  # 通过标题查询乐曲
[绿|黄|红|紫|白]id<乐曲编号>  # 通过查询乐曲或谱面
<乐曲别名>是什么歌  # 查询乐曲别名对应的乐曲
(添加|删除)别名 <乐曲id> <乐曲别名>  # 添加/删除乐曲别名
定数查歌 <定数>  # 查询定数对应的乐曲
定数查歌 <定数下限> <定数上限>
分数线 <难度+歌曲id> <分数线>  # 详情请输入“分数线 帮助”查看
'''.strip()


@help.handle()
async def help_func() -> None:
    await help.finish(MessageSegment.image(text_to_image_base64_str(help_str)))


def music_info(music: Music) -> Message:
    return Message([
        MessageSegment.image(f'https://www.diving-fish.com/covers/{get_cover_len4_id(music["id"])}.png'),
        MessageSegment.text(f"{music.id}. {music.title}\n"),
        MessageSegment.text(f'艺术家：{music.artist}\n'
                            f'分类：{music.genre}\n'
                            f'速度：{music.bpm}bpm\n'
                            f'版本：{music.version}\n'
                            f'等级：{" / ".join(music.level)}\n'
                            f'定数：{" / ".join(map(str, music.ds))}')])


def music_info_compact(music: Music) -> str:
    return f'{music.id}. {music.title} {" / ".join(map(str, music.ds))}'


def music_info_with_diff_compact(music: Music, diff: int) -> str:
    return f'{music.id}. {music.title} {DIFFICULTY_NAME[diff]} {music.level[diff]} ({music.ds[diff]})'


def chart_info(music: Music, diff_index: int) -> Message:
    chart: Chart = music.charts[diff_index]
    ds: float = music.ds[diff_index]
    level: str = music.level[diff_index]
    if len(chart['notes']) == 4:
        msg: str = (f'{DIFFICULTY_NAME[diff_index]} {level} ({ds})\n'
                    f'TAP: {chart.tap}\n'
                    f'HOLD: {chart.hold}\n'
                    f'SLIDE: {chart.slide}\n'
                    f'BREAK: {chart.break_}\n'
                    f'谱师: {chart.charter}')
    else:
        msg: str = (f'{DIFFICULTY_NAME[diff_index]} {level} ({ds})\n'
                    f'TAP: {chart.tap}\n'
                    f'HOLD: {chart.hold}\n'
                    f'SLIDE: {chart.slide}\n'
                    f'TOUCH: {chart.touch}\n'
                    f'BREAK: {chart.break_}\n'
                    f'谱师: {chart.charter}')
    return Message([
        MessageSegment.image(f'https://www.diving-fish.com/covers/{get_cover_len4_id(music["id"])}.png'),
        MessageSegment.text(f'{music.id}. {music.title}\n'),
        MessageSegment.text(msg)
    ])


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
        await search_music_by_inner.finish('命令格式为\n'
                                           '定数查歌 <定数>\n'
                                           '定数查歌 <定数下限> <定数上限>')

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


@spec_rand.handle()
async def spec_rand_func(group: tuple[str | None, str | None, str] = RegexGroup()) -> None:
    music_type: str | None = None
    if group[0] is not None:
        if group[0].lower() == "dx":
            music_type = "DX"
        elif group[0].lower() == "sd" or group[0] == "标准":
            music_type = "SD"
    level: str = group[2]
    if group[1] is None:
        diff = None
    else:
        diff = ['绿黄红紫白'.index(group[1])]
    music_data: MusicList = Mai.music_list.filter(level=level, diff=diff, type=music_type)
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
    s = f"今日人品值：{luck}\n"
    for i in range(len(wm_list)):
        if wm_value[i] == 3:
            s += f'宜 {wm_list[i]}\n'
        elif wm_value[i] == 0:
            s += f'忌 {wm_list[i]}\n'
    s += "Bio提醒您：打机时不要大力拍打或滑动哦\n今日推荐歌曲："
    music = Mai.music_list[hash_value % len(Mai.music_list)]
    await today_maimai.finish(Message([MessageSegment("text", {"text": s})] + music_info(music)))


@query_score.handle()
async def query_score_func(event: Event, message: Message = CommandArg()):
    r = "([绿黄红紫白])(id)?([0-9]+)"
    argv = str(message).strip().split(" ")
    if len(argv) == 1 and argv[0] == '帮助':
        s = '''此功能为查找某首歌分数线设计。
命令格式：分数线 <难度+歌曲id> <分数线>
例如：分数线 紫799 100
命令将返回分数线允许的 TAP GREAT 容错以及 BREAK 50落等价的 TAP GREAT 数。
以下为 TAP GREAT 的对应表：
GREAT/GOOD/MISS
TAP\t1/2.5/5
HOLD\t2/5/10
SLIDE\t3/7.5/15
TOUCH\t1/2.5/5
BREAK\t5/12.5/25(外加200落)'''
        await query_score.send(Message([
            MessageSegment("image", {
                "file": f"base64://{str(image_to_base64(text_to_image(s)), encoding='utf-8')}"
            })
        ]))
    elif len(argv) == 2:
        try:
            grp = re.match(r, argv[0]).groups()
            level_labels = ['绿', '黄', '红', '紫', '白']
            level_labels2 = ['Basic', 'Advanced',
                             'Expert', 'Master', 'Re:MASTER']
            level_index = level_labels.index(grp[0])
            chart_id = grp[2]
            line = float(argv[1])
            music = Mai.music_list.by_id(chart_id)
            chart: dict = music['charts'][level_index]
            tap = int(chart['notes'][0])
            slide = int(chart['notes'][2])
            hold = int(chart['notes'][1])
            touch = int(chart['notes'][3]) if len(chart['notes']) == 5 else 0
            brk = int(chart['notes'][-1])
            total_score = 500 * tap + slide * 1500 + hold * 1000 + touch * 500 + brk * 2500
            break_bonus = 0.01 / brk
            break_50_reduce = total_score * break_bonus / 4
            reduce = 101 - line
            if reduce <= 0 or reduce >= 101:
                raise ValueError
            await query_chart.send(f'''{music['title']} {level_labels2[level_index]}
分数线 {line}% 允许的最多 TAP GREAT 数量为 {(total_score * reduce / 10000):.2f}(每个-{10000 / total_score:.4f}%),
BREAK 50落(一共{brk}个)等价于 {(break_50_reduce / 100):.3f} 个 TAP GREAT(-{break_50_reduce / total_score * 100:.4f}%)''')
        except Exception:
            await query_chart.send("格式错误，输入“分数线 帮助”以查看帮助信息")


@best_40_pic.handle()
async def best_40_pic_func(event: Event, message: Message = CommandArg()):
    username: str = str(message).strip()
    if username == '':
        payload: dict[str, str] = {'qq': str(event.get_user_id())}
    else:
        if username.isdigit():
            payload = {'qq': username}
        elif message[0].type == 'at':
            payload = {'qq': str(message[0].data['qq'])}
        else:
            payload = {'username': username}
    img, success = await generate(payload)
    if success == 400:
        await best_40_pic.send("未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。")
    elif success == 403:
        await best_40_pic.send("该用户禁止了其他人获取数据。")
    else:
        await best_40_pic.send(MessageSegment.image(f"base64://{str(image_to_base64(img), encoding='utf-8')}"))


@best_50_pic.handle()
async def best_50_pic_func(event: Event, message: Message = CommandArg()):
    username: str = str(message).strip()
    if username == '':
        payload: dict[str, str] = {'qq': str(event.get_user_id())}
    else:
        if username.isdigit():
            payload = {'qq': username}
        elif message[0].type == 'at':
            payload = {'qq': str(message[0].data['qq'])}
        else:
            payload = {'username': username}
    img, success = await generate50(payload)
    if success == 400:
        await best_50_pic.send("未找到此玩家，请确保此玩家的用户名和查分器中的用户名相同。")
    elif success == 403:
        await best_50_pic.send("该用户禁止了其他人获取数据。")
    else:
        await best_50_pic.send(MessageSegment.image(f"base64://{str(image_to_base64(img), encoding='utf-8')}"))


@plate_process.handle()
async def plate_process_func(bot: Bot, event: Event, message: Message = EventMessage()):
    match = re.match(plate_process_regex, str(message).strip())
    version_han, plate_name_han, nickname = match.groups()
    if f'{version_han}{plate_name_han}' == '真将':
        await plate_process.finish('真系没有真将哦')

    payload = dict()
    qqid = event.get_user_id()
    for message_segment in message:
        if message_segment.type == 'at' and message_segment.data['qq'] != 'all':
            qqid = int(message_segment.data['qq'])
            payload['qq'] = qqid
            # logger.debug('\n'.join([repr(message_segment), repr(
            #     message_segment.type), repr(message_segment.data)]))

    if nickname:
        if nickname.isdigit():
            qqid = int(nickname)
            payload['qq'] = qqid
    else:
        payload['qq'] = qqid
    if 'qq' not in payload:
        payload['username'] = nickname

    if qqid != event.user_id:
        nickname = (await bot.get_stranger_info(user_id=qqid))['nickname']

    if match.group(1) in {'霸', '舞'}:
        payload['version'] = list(
            set(version for version in list(maimaidx_plate.plate_to_version.values())[:-5]))
    else:
        payload['version'] = [maimaidx_plate.plate_to_version[version_han]]
    data = await maimaidx_plate.player_plate_data(payload, match, nickname)
    await plate_process.send(data)
