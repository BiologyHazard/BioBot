import re
from typing import Any

from nonebot import MatcherGroup, get_driver, logger
from nonebot.adapters.onebot.v11 import (Bot, Event, Message, MessageEvent,
                                         MessageSegment)
from nonebot.drivers import Driver
from nonebot.params import CommandArg, EventMessage, RegexGroup
from nonebot.typing import T_State

from . import maimaidx_plate
from .image import image_to_base64, text_to_image, text_to_image_base64_str
from .maimai_best_40 import generate
from .maimai_best_50 import generate50
from .maimaidx_music import (Music, MusicList, aliases_dict, get_aliases,
                             get_cover_len4_id, get_music, total_list)
from .utils import get_hash_value

driver: Driver = get_driver()


@driver.on_startup
async def on_startup_func() -> None:
    '''
    bot启动时开始获取所有数据
    '''
    await get_music()
    await get_aliases()

maimai_command_group = MatcherGroup(priority=3, block=False)
help = maimai_command_group.on_command('help maimai')
today_maimai = maimai_command_group.on_command('今日舞萌', aliases={'今日mai', 'jrwm'})
search_music_by_inner = maimai_command_group.on_command('定数查歌')
spec_rand = maimai_command_group.on_regex(r"(?i)随个(dx|sd|标准)?(绿|黄|红|紫|白)?([0-9]+\+?)")
maimai_what = maimai_command_group.on_regex(r"(?i).*maimai.*什么")
query_chart = maimai_command_group.on_regex(r"^([绿黄红紫白]?)id([0-9]+)")
search_music = maimai_command_group.on_command('查歌')
query_score = maimai_command_group.on_command('分数线')
best_40_pic = maimai_command_group.on_command('b40')
best_50_pic = maimai_command_group.on_command('b50')
query_music_by_alias = maimai_command_group.on_regex(r'(.*)是什么歌')
add_alias = maimai_command_group.on_command('添加别名')
delete_alias = maimai_command_group.on_command('删除别名')
plate_process_regex = r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽舞霸])([極极将舞神者]舞?)进度\s?(.+)?'
plate_process = maimai_command_group.on_regex(plate_process_regex)

help_str: str = '''
可用命令如下：
今日舞萌  # 查看今天的舞萌运势
(b40|b50)[@某人|qq号|水鱼网昵称]  # 查询自己或别人的b40/b50
[...]maimai[...]什么  # 随机一首歌
随个[dx|标准][绿|黄|红|紫|白]<难度>  # 随机一首指定条件的乐曲
查歌<乐曲标题的一部分>  # 查询符合条件的乐曲
[绿|黄|红|紫|白]id<乐曲编号>  # 查询乐曲信息或谱面信息
<乐曲别名>是什么歌  # 查询乐曲别名对应的乐曲
(添加|删除)别名 <乐曲id> <乐曲别名>  # 添加/删除乐曲别名
定数查歌 <定数>  # 查询定数对应的乐曲
定数查歌 <定数下限> <定数上限>
分数线 <难度+歌曲id> <分数线>  # 详情请输入“分数线 帮助”查看
'''.strip()


@help.handle()
async def help_func() -> None:
    await help.finish(MessageSegment.image(text_to_image_base64_str(help_str)))


def song_txt(music: Music) -> Message:
    return Message([
        MessageSegment.text(f"{music.id}. {music.title}\n"),
        MessageSegment.image(f"https://www.diving-fish.com/covers/{get_cover_len4_id(music.id)}.png"),
        MessageSegment.text(f"\n{'/'.join(music.level)}")
    ])


def inner_level_q(ds1, ds2=None):
    result = []
    diff_label = ['Bas', 'Adv', 'Exp', 'Mst', 'ReM']
    if ds2 is not None:
        music_data = total_list.filter(ds=(ds1, ds2))
    else:
        music_data = total_list.filter(ds=ds1)
    for music in sorted(music_data, key=lambda i: int(i['id'])):
        for i in music.diff:
            result.append(
                (music['id'], music['title'], music['ds'][i], diff_label[i], music['level'][i]))
    return result


@search_music_by_inner.handle()
async def search_music_by_inner_func(event: Event, message: Message = CommandArg()):
    argv: list[str] = str(message).strip().split(" ")
    if len(argv) > 2 or len(argv) == 0:
        await search_music_by_inner.finish("命令格式为\n定数查歌 <定数>\n定数查歌 <定数下限> <定数上限>")
    if len(argv) == 1:
        result_set = inner_level_q(float(argv[0]))
    else:
        result_set = inner_level_q(float(argv[0]), float(argv[1]))
    if len(result_set) > 50:
        await search_music_by_inner.finish(f"结果过多（{len(result_set)} 条），请缩小搜索范围。")
    s = ""
    for elem in result_set:
        s += f"{elem[0]}. {elem[1]} {elem[3]} {elem[4]}({elem[2]})\n"
    await search_music_by_inner.finish(s.strip())


@spec_rand.handle()
async def _(event: MessageEvent, message: Message = EventMessage(), group: tuple = RegexGroup()):
    level_labels = ['绿', '黄', '红', '紫', '白']
    regex = "随个((?:dx|sd|标准))?([绿黄红紫白]?)([0-9]+\+?)"
    res = re.match(regex, str(message).lower())
    try:
        tp: str | None = None
        if group[0] is not None:
            if group[0].lower() == "dx":
                tp = "DX"
            elif group[0].lower() == "sd" or group[0] == "标准":
                tp = "SD"
        level = group[2]
        if group[1] is None:
            diff = None
        else:
            diff = ['绿黄红紫白'.index(group[1])]
        music_data: MusicList = total_list.filter(level=level, diff=diff, type=tp)
        if len(music_data) == 0:
            rand_result = "没有这样的乐曲哦。"
        else:
            rand_result = song_txt(music_data.random())
        await spec_rand.send(rand_result)
    except Exception as e:
        logger.error(e)
        await spec_rand.finish("随机命令错误，请检查语法")


@maimai_what.handle()
async def maimai_what_func() -> None:
    await maimai_what.finish(song_txt(total_list.random()))


@search_music.handle()
async def search_music_func(event: Event, message: Message = CommandArg()):
    name = str(message)
    if not name:
        await search_music.finish('请输入要查询的歌曲。')
    res: MusicList = total_list.filter(title_search=name)
    if len(res) == 0:
        await search_music.send("没有找到这样的乐曲。")
    elif len(res) < 50:
        search_result = ""
        for music in sorted(res, key=lambda i: int(i['id'])):
            search_result += f"{music['id']}. {music['title']}\n"
        await search_music.finish(search_result.strip())
    else:
        await search_music.send(f"结果过多（{len(res)}条），请缩小查询范围。")


@query_chart.handle()
async def _(event: Event, message: Message = EventMessage()):
    regex = "([绿黄红紫白]?)id([0-9]+)"
    groups = re.match(regex, str(message)).groups()
    level_labels = ['绿', '黄', '红', '紫', '白']
    if groups[0] != "":
        try:
            level_index = level_labels.index(groups[0])
            level_name = ['Basic', 'Advanced',
                          'Expert', 'Master', 'Re: MASTER']
            name = groups[1]
            music = total_list.by_id(name)
            chart = music['charts'][level_index]
            ds = music['ds'][level_index]
            level = music['level'][level_index]
            file = f"https://www.diving-fish.com/covers/{get_cover_len4_id(music['id'])}.png"
            if len(chart['notes']) == 4:
                msg = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
BREAK: {chart['notes'][3]}
谱师: {chart['charter']}'''
            else:
                msg = f'''{level_name[level_index]} {level}({ds})
TAP: {chart['notes'][0]}
HOLD: {chart['notes'][1]}
SLIDE: {chart['notes'][2]}
TOUCH: {chart['notes'][3]}
BREAK: {chart['notes'][4]}
谱师: {chart['charter']}'''
            await query_chart.send(Message([
                MessageSegment("text", {"text": f"{music['id']}. {music['title']}\n"}),
                MessageSegment("image", {"file": f"{file}"}),
                MessageSegment("text", {"text": msg})
            ]))
        except Exception:
            await query_chart.send("未找到该谱面")
    else:
        name = groups[1]
        music = total_list.by_id(name)
        try:
            file = f"https://www.diving-fish.com/covers/{get_cover_len4_id(music['id'])}.png"
            await query_chart.send(Message([
                MessageSegment("text", {
                    "text": f"{music['id']}. {music['title']}\n"
                }),
                MessageSegment("image", {
                    "file": f"{file}"
                }),
                MessageSegment("text", {
                    "text": f"艺术家: {music['basic_info']['artist']}\n分类: {music['basic_info']['genre']}\nBPM: {music['basic_info']['bpm']}\n版本: {music['basic_info']['from']}\n难度: {'/'.join(music['level'])}"
                })
            ]))
        except Exception:
            await query_chart.send("未找到该乐曲")


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
    music = total_list[hash_value % len(total_list)]
    await today_maimai.finish(Message([MessageSegment("text", {"text": s})] + song_txt(music)))


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
            music = total_list.by_id(chart_id)
            chart: dict[Any] = music['charts'][level_index]
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
        await best_40_pic.send(Message([
            MessageSegment("image", {
                "file": f"base64://{str(image_to_base64(img), encoding='utf-8')}"
            })
        ]))


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


@query_music_by_alias.handle()
async def query_music_by_alias_func(message: Message = EventMessage(), group: tuple[str] = RegexGroup()):
    (query_alias,) = group
    aliases_dict.by_alias(query_alias)
    ...


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
    # if not hasattr(mai, 'total_list'):
    #     await mai.get_music()
    # logger.debug('\n'.join([repr(payload)]))
    data = await maimaidx_plate.player_plate_data(payload, match, nickname)
    await plate_process.send(data)
