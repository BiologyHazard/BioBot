import asyncio
import json
import math
import re
from bisect import bisect_right
from random import Random
from typing import Any

import aiofiles
from nonebot import MatcherGroup, get_driver, logger, require
from nonebot.adapters.onebot.v11 import (Bot, GroupMessageEvent, Message,
                                         MessageEvent, MessageSegment,
                                         PrivateMessageEvent)
from nonebot.adapters.onebot.v11.permission import GROUP_ADMIN, GROUP_OWNER
from nonebot.drivers import Driver
from nonebot.params import CommandArg, EventMessage, EventPlainText, RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import Rule

from .achievement_pic import generate_achievement_pic
from .api_data import get_player_data, get_rating_ranking_data
from .best50 import generate_b50
from .config import plugin_config
from .consts import (COMBO_RANK, DIFFICULTY_NAME, LEVELS, SYNC_RANK,
                     VERSION_TO_PLATE, combo_rank, sync_rank)
from .guess import Guess, guesses
from .image import image_to_bytesio, text_to_image
from .music import (AliasInfo, Chart, ChartStats, Mai, Music, MusicList,
                    compute_rating)
from .plate import player_plate_data
from .privacy import set_privacy as privacy_set_privacy
from .stats_pic import chart_stats_text
from .utils import get_random_inst, strftime

require('nonebot_plugin_apscheduler')
from nonebot_plugin_apscheduler import scheduler  # NOQA: E402

driver: Driver = get_driver()
default_command_start: str = tuple(driver.config.command_start)[0]

# 【如何阅读本帮助】
# · "|" 表示“或”
# · 尖括号"<>" 表示需要一个参数
# · 方括号"[]" 表示“可选”
# · "(A|B)" 表示“A或B”
help_str: str = f'''
欢迎使用 BioBot 的 maimai插件！
本插件魔改自 Diving-Fish/mai-bot 和 Yuri-YuzuChaN/maimaiDX
maimai插件可用命令如下：

【插件帮助】
· {default_command_start}help maimai\t# 查看本帮助

【随机乐曲】
· {default_command_start}(今日舞萌|今日mai)\t# 查看今天的舞萌运势
· [...]maimai[...]什么\t# 随机一首乐曲
· 随个[dx|sd|标准][绿|黄|红|紫|白]<等级|定数>\t# 随机一首指定条件的乐曲

【查询成绩】
· {default_command_start}b50 [<@某人|qq号|水鱼网用户名>]\t# 查询b50
· {default_command_start}乐曲成绩 <乐曲id|标题|别名> [<@某人|qq号|水鱼网用户名>]\t# 查询乐曲成绩
· <牌子名称>进度 [<@某人|qq号|水鱼网用户名>]\t# 查询牌子进度
· <牌子名称>完成表 [<@某人|qq号|水鱼网用户名>]\t# 查询牌子完成表
# TODO: · <等级|定数>进度 [<@某人|qq号|水鱼网用户名>]\t# 查询制霸进度
· <等级|定数|版本|难度>[<目标>]完成表 [<@某人|qq号|水鱼网用户名>]\t# 查询完成表
    例：14+SSS完成表，14.0FSD完成表，舞代AP完成表，紫谱完成表（紫谱FC完成表）
    # “目标”可以是连击评价、同步率评价或达成率评价，默认为"A"
· <等级|定数>成绩列表\t# 查询成绩列表
· <等级|定数>成绩列表 <页码> [<@某人|qq号|水鱼网用户名>]
· {default_command_start}rating排名 [<@某人|qq号|水鱼网用户名>]\t# 查询rating排名

【查询乐曲】
# TODO: · <等级>定数表\t# 查询定数表
· [绿|黄|红|紫|白]id<乐曲id>\t# 通过id查询乐曲或谱面
· {default_command_start}查歌 <乐曲标题的一部分>\t# 通过标题查询乐曲
· <乐曲别名>是什么歌\t# 通过别名查询乐曲
· {default_command_start}定数查歌 <定数>\t# 通过定数查询乐曲
· {default_command_start}定数查歌 <定数下限> <定数上限> [<页码>]
· {default_command_start}bpm查歌 <曲速>\t# 通过曲速查询乐曲
· {default_command_start}bpm查歌 <曲速下限> <曲速上限> [<页码>]
· {default_command_start}曲师查歌 <艺术家> [<页码>]\t# 通过艺术家查询乐曲
· {default_command_start}谱师查歌 <谱师> [<页码>]\t# 通过谱师查询谱面
· {default_command_start}谱面统计 [绿|黄|红|紫|白]<乐曲id|标题|别名>\t# 查询谱面的统计信息

【乐曲别名】
· {default_command_start}(添加|删除)别名 <乐曲id> <乐曲别名>\t# 添加/删除乐曲别名
· {default_command_start}查询别名 <乐曲id|标题|别名>\t# 查询乐曲别名

【推分助手】
· {default_command_start}分数线 (绿|黄|红|紫|白)<乐曲id> <分数线>\t# 详情请输入“分数线 帮助”查看

【猜歌游戏】
· {default_command_start}猜歌\t# 开始猜歌

【隐私设置】
· {default_command_start}(同意|允许|禁止|拒绝|不允许)其他人查询我的成绩
  # 由于水鱼网api的特性，即使您在水鱼网勾选了“禁止其他人查询我的成绩”，
  # BioBot仍可以通过qq号查询您的成绩，
  # 如果您不希望其他人使用BioBot查询您的成绩，
  # 可以使用上面的命令更改隐私设置。
  # 请注意：这条命令仅在BioBot中起作用，
  # BioBot没有能力阻止其他人通过您的qq号查询成绩，
  # 如果您仍有顾虑，您可以选择在水鱼网中解除绑定qq号。
'''.strip()

__plugin_meta__ = PluginMetadata(
    name='maimai',
    description='maimai查分/查歌/随机/查别名/查定数/查分数线',
    usage=help_str
)


@scheduler.scheduled_job('cron', hour=0)
@driver.on_startup
async def on_startup_func() -> None:
    '''bot启动时获取曲目信息和别名信息'''
    await Mai.get_music()
    await Mai.get_aliases()


def get_event_id(bot: Bot, event: MessageEvent) -> str:
    if isinstance(event, PrivateMessageEvent):
        return f'{bot.self_id}_{event.sub_type}_{event.user_id}'
    elif isinstance(event, GroupMessageEvent):
        return f'{bot.self_id}_{event.sub_type}_{event.group_id}'
    raise TypeError


@Rule
def no_command_arg(command_arg: Message = CommandArg()) -> bool:
    return not command_arg


@Rule
def not_anonymous(event: MessageEvent) -> bool:
    return not (isinstance(event, GroupMessageEvent) and event.sub_type == 'anonymous')


def is_now_playing_guess_music(bot: Bot, event: MessageEvent) -> bool:
    return get_event_id(bot, event) in guesses


maimai_command_group = MatcherGroup(priority=3, block=False)
# 插件帮助
help = maimai_command_group.on_command('help maimai', rule=no_command_arg)
# 随机乐曲
today_maimai = maimai_command_group.on_command(
    '今日舞萌', aliases={'今日mai', 'jrwm', '今日乌蒙'}, rule=no_command_arg & not_anonymous)
maimai_what = maimai_command_group.on_regex(r'maimai.*什么', flags=re.RegexFlag.IGNORECASE)
spec_rand = maimai_command_group.on_regex(
    r'[随来给]个(dx|sd|标准)?(绿|黄|红|紫|白)?(?:(\d{1,2}\.\d)|(\d{1,2}\+?))', flags=re.RegexFlag.IGNORECASE)
# 查询成绩
best_50 = maimai_command_group.on_command('b50', aliases={'best50'}, rule=not_anonymous)
plate_process = maimai_command_group.on_regex(
    r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽煌宙星祭舞](?:[極极将神舞]|舞舞)|霸者)进度\s*(.*)', rule=not_anonymous)
# plate_process_pic = maimai_command_group.on_regex(
#     r'^([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽煌宙星祭舞霸]代?|\d{1,2}\.\d|\d{1,2}\+?|[绿黄红紫白]谱?)([極极将神舞者]|舞舞|D|C|B{1,3}|A{1,3}|S{1,3}[p+]?|F[CS][p+]?|AP[p+]?|FSD\+?|FDX\+?)完成表\s*(.*)', rule=not_anonymous)
process_pic = maimai_command_group.on_regex(
    r'^(([真超檄橙暁晓桃櫻樱紫菫堇白雪輝辉熊華华爽煌宙星祭舞]代?|霸(?=者))|(\d{1,2}\.\d)|(\d{1,2}\+?)|([绿黄红紫白]谱))'
    r'(([極极将神舞]|舞舞|(?<=霸)者)|(D|C|B{1,3}|A{1,3}|S{1,3}[p+]?)|(FC[p+]?|AP[p+]?)|(FSD?[p+]?|FDX[p+]?)|)'
    r'完成表\s*(.*)',
    flags=re.RegexFlag.IGNORECASE, rule=not_anonymous)
level_achievement = maimai_command_group.on_regex(
    r'^(?:(\d{1,2}\.\d)|(\d{1,2}\+?))(?:成绩|分数)列表\s*(\d+)?\s*(.+)?', rule=not_anonymous)
music_score = maimai_command_group.on_command(
    '乐曲成绩', aliases={'歌曲成绩', '我的成绩', '查成绩', 'minfo', '查分', '乐曲分数', '歌曲分数'}, rule=not_anonymous)
rating_ranking = maimai_command_group.on_command(
    'rating排名', aliases={'我的排名', '我有多菜'}, rule=not_anonymous)
# 查询乐曲
query_chart = maimai_command_group.on_regex(r'^(绿|黄|红|紫|白)?\s*id\s*(\d+)')
search_music_by_title = maimai_command_group.on_command('查歌')
search_music_by_alias = maimai_command_group.on_regex(r'(.*)(?:是什么歌|是啥歌)')
search_music_by_inner = maimai_command_group.on_command('定数查歌')
search_music_by_tempo = maimai_command_group.on_command('bpm查歌')
search_music_by_artist = maimai_command_group.on_command('曲师查歌')
search_music_by_charter = maimai_command_group.on_command('谱师查歌')
chart_stats = maimai_command_group.on_command('谱面统计', aliases={'统计信息', 'ginfo'})
# 乐曲别名
add_alias = maimai_command_group.on_command(
    '添加别名', aliases={'添加别称', '增加别名', '增加别称'}, rule=not_anonymous)
delete_alias = maimai_command_group.on_command('删除别名', aliases={'删除别称'}, rule=not_anonymous)
query_alias = maimai_command_group.on_command('查询别名', rule=not_anonymous)
# query_alias = maimai_command_group.on_regex(r'(.*)有什么别名')
# 推分助手
score_line = maimai_command_group.on_command('分数线')
# 猜歌游戏
guess_music_start = maimai_command_group.on_command('猜歌', rule=no_command_arg)
guess_music_solve = maimai_command_group.on_message(rule=is_now_playing_guess_music)
# 隐私设置
set_privacy = maimai_command_group.on_keyword(
    {'他人查询我的成绩', '他人查询成绩', '他人查询自己的成绩'}, rule=not_anonymous)


search_music_by_inner_help_text: str = f'''
命令格式为
· {default_command_start}定数查歌 <定数>  # 查询定数对应的乐曲
· {default_command_start}定数查歌 <定数下限> <定数上限>
'''.strip()

search_music_by_tempo_help_text: str = f'''
命令格式为：
· {default_command_start}bpm查歌 <曲速>  # 通过曲速查询乐曲
· {default_command_start}bpm查歌 <曲速下限> <曲速上限> [<页码>]
'''.strip()

search_music_by_artist_help_text: str = f'''
命令格式为：
· {default_command_start}曲师查歌 <艺术家> [<页码>]  # 通过艺术家查询乐曲
'''.strip()

search_music_by_charter_help_text: str = f'''
命令格式为：
· {default_command_start}谱师查歌 <谱师> [<页码>]    # 通过谱师查询谱面
'''.strip()

query_score_help_text: str = '''
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
    return None


async def get_payload_and_nickname(bot: Bot, event: MessageEvent, message: Message, user: str | None = None) -> tuple[dict[str, Any], str]:
    payload: dict[str, Any] = {}
    if (qqid := get_at_qq(message)) is not None:
        payload['qq'] = qqid
        nickname: str = (await bot.get_stranger_info(user_id=qqid))['nickname'] or str(qqid)
    elif user is not None and user.strip():
        user = user.strip()
        if user.isdigit():
            stranger_nickname: str = (await bot.get_stranger_info(user_id=int(user)))['nickname']
            if not stranger_nickname:
                payload['username'] = nickname = user
            else:
                payload['qq'] = int(user)
                nickname = stranger_nickname
        else:
            payload['username'] = nickname = user
    else:
        payload['qq'] = event.user_id
        nickname = (await bot.get_stranger_info(user_id=event.user_id))['nickname'] or str(qqid)

    return payload, nickname


# async def get_qq_or_username(bot: Bot, event: MessageEvent, message: Message, user: str | None = None) -> tuple[int, None] | tuple[None, str]:
#     if (qqid := get_at_qq(message)) is not None:
#         return qqid, None
#     elif user is not None and user.strip():
#         user = user.strip()
#         if user.isdigit():
#             stranger_nickname: str = (await bot.get_stranger_info(user_id=int(user)))['nickname']
#             if not stranger_nickname:
#                 return None, user
#             else:
#                 return int(user), None
#         else:
#             return None, user
#     else:
#         return event.user_id, None


# async def get_payload(qqid: int | None = None, username: str | None = None)


async def music_info(music: Music) -> Message:
    return Message([
        MessageSegment.image(await music.get_cover()),
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


async def chart_info(music: Music, diff_index: int) -> Message:
    chart: Chart = music.charts[diff_index]
    ds: float = music.ds[diff_index]
    level: str = music.level[diff_index]
    return Message([
        MessageSegment.image(await music.get_cover()),
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
    await help.finish(MessageSegment.image(image_to_bytesio(text_to_image(help_str, tabs=[35]))))


wm_list: list[str] = ['拼机', '推分', '越级', '下埋', '夜勤', '练底力', '练手法', '打旧框', '干饭', '抓绝赞', '收歌']


@today_maimai.handle()
async def today_maimai_func(event: MessageEvent) -> None:
    random_inst: Random = get_random_inst(event.user_id)
    luck: int = random_inst.randint(0, 100)
    wm_value: list[int] = [random_inst.randrange(4) for _ in wm_list]
    lines: list[str] = []
    lines.append(f'今日人品值：{luck}')
    for value, content in zip(wm_value, wm_list):
        if value == 3:
            lines.append(f'宜 {content}')
        elif value == 0:
            lines.append(f'忌 {content}')
    lines.append('Bio提醒您：打机时不要大力拍打或滑动哦')
    lines.append('今日推荐歌曲：')
    music: Music = random_inst.choice(Mai.music_list)
    await today_maimai.finish(Message([MessageSegment.text('\n'.join(lines))]) + await music_info(music))


@maimai_what.handle()
async def maimai_what_func() -> None:
    await maimai_what.finish(await music_info(Mai.music_list.random()))


@spec_rand.handle()
async def spec_rand_func(group: tuple[str | None, str | None, str | None, str | None] = RegexGroup()) -> None:
    music_type, diff, ds, level = group
    if ds is not None:
        ds = float(ds)
        assert math.isfinite(ds), ValueError
    if music_type is not None:
        if music_type.lower() == 'dx':
            music_type = 'DX'
        elif music_type.lower() == 'sd' or group[0] == '标准':
            music_type = 'SD'
    if diff is None:
        diff_index = None
    else:
        diff_index = ['绿黄红紫白'.index(diff)]
    music_data: MusicList = Mai.music_list.filter(level=level, ds=ds, diff=diff_index, type_=music_type)
    if len(music_data) == 0:
        await spec_rand.finish('没有这样的乐曲哦。')
    else:
        await spec_rand.finish(await music_info(music_data.random()))


@best_50.handle()
async def best_pic_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    payload, nickname = await get_payload_and_nickname(bot, event, message, message.extract_plain_text())

    result: MessageSegment | str = await generate_b50(payload, event.user_id)
    await best_50.finish(result)


@music_score.handle()
async def music_score_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    args: list[str] = message.extract_plain_text().strip().rsplit(maxsplit=1)
    if len(args) == 1:
        (name, ) = args
        user = None
    else:
        name, user = args

    matched_music: MusicList = Mai.music_list.by_name(name)
    if not matched_music:
        await music_score.finish(f'没有找到id/标题/别名为{name}的乐曲。')
    if len(matched_music) > 1:
        await music_score.finish(f'“{name}”匹配{len(matched_music)}首乐曲：\n'
                                 + '\n'.join(music_info_compact(music) for music in matched_music)
                                 + '\n请发送乐曲的id以确定查询的乐曲。')

    (music,) = matched_music
    payload, nickname = await get_payload_and_nickname(bot, event, message, user)
    payload['version'] = [music.version]
    data: dict[str, Any] | str = await get_player_data('plate', payload, event.user_id)

    if isinstance(data, str):
        await music_score.finish(data)

    player_data: list[dict[str, Any]] = [x for x in data['verlist'] if str(x['id']) == music.id]
    if not player_data:
        await music_score.finish(f'{nickname}未游玩{music.id}. {music.title}', at_sender=True)

    messages: list[str] = [f'{nickname}的乐曲成绩\n'
                           f'{music.id}. {music.title}\n']
    for achievement_data in sorted(player_data, key=lambda x: x['level_index']):
        level_index: int = achievement_data['level_index']
        achievement: float = achievement_data['achievements']
        messages.append(f'{DIFFICULTY_NAME[level_index]} {music.ds[level_index]} | {achievement:.4f}% → {compute_rating(music.ds[level_index], achievement)}')
        if achievement_data['fc']:
            messages.append(f' | {COMBO_RANK[combo_rank.index(achievement_data["fc"])]}')
        if achievement_data['fs']:
            messages.append(f' {SYNC_RANK[sync_rank.index(achievement_data["fs"])]}')
        messages.append('\n')
    await music_score.finish(''.join(messages), at_sender=True)


@plate_process.handle()
async def plate_process_func(bot: Bot, event: MessageEvent, message: Message = EventMessage(), group: tuple[str, str] = RegexGroup()) -> None:
    plate_name_han, user = group
    version_han, goal_han = plate_name_han[0], plate_name_han[1]

    payload, nickname = await get_payload_and_nickname(bot, event, message, user)

    data: MessageSegment | str = await player_plate_data(payload, version_han, goal_han, nickname, event.user_id)
    await plate_process.finish(data)


@process_pic.handle()
async def process_pic_func(
        bot: Bot,
        event: MessageEvent,
        message: Message = EventMessage(),
        group: tuple[str, str | None, str | None, str | None, str | None,
                     str, str | None, str | None, str | None, str | None, str] = RegexGroup(),
) -> None:
    user = group[-1]
    payload, nickname = await get_payload_and_nickname(bot, event, message, user)

    data: MessageSegment | str = await generate_achievement_pic(payload, group, event.user_id)
    await process_pic.finish(data)


@level_achievement.handle()
async def level_achievement_func(bot: Bot, event: MessageEvent, message: Message = EventMessage(), group: tuple[str | None, str | None, str | None, str | None] = RegexGroup()) -> None:
    ds, level, page, user = group
    if level is not None and level not in LEVELS:
        await level_achievement.finish(f'不存在等级为{level}的乐曲。', reply_message=True)

    if ds is not None and not Mai.music_list.min_ds <= float(ds) <= Mai.music_list.max_ds:
        await level_achievement.finish(f'不存在定数为{ds}的乐曲。', reply_message=True)

    payload, nickname = await get_payload_and_nickname(bot, event, message, user)
    payload['version'] = list(version for version in VERSION_TO_PLATE)
    data: dict[str, list[dict[str, Any]]] | str = await get_player_data('plate', payload, event.user_id)
    if isinstance(data, str):
        await level_achievement.finish(data, reply_message=True)

    achievement_list: list[tuple[Music, dict[str, Any]]] = []
    if ds is not None:
        for achievement_data in data['verlist']:
            music: Music = Mai.music_list.by_id(str(achievement_data['id']), strict=True)
            if math.isclose(music.ds[achievement_data['level_index']], float(ds)):
                achievement_list.append((music, achievement_data))
    else:
        for achievement_data in data['verlist']:
            if achievement_data['level'] == level:
                music: Music = Mai.music_list.by_id(str(achievement_data['id']), strict=True)
                achievement_list.append((music, achievement_data))

    pages: int = math.ceil(len(achievement_list) / plugin_config.songs_per_page)
    page: str | int | None = max(min(int(page) - 1, pages - 1), 0) if page else 0

    messages: list[str] = [f'{nickname}的{ds or level}分数列表（从高至低）：\n']
    for i, (music, achievement_data) in enumerate(sorted(achievement_list,
                                                         key=lambda x: x[1]['achievements'], reverse=True)):
        if page * plugin_config.songs_per_page <= i < (page + 1) * plugin_config.songs_per_page:
            messages.append(f'No.{i+1} | {achievement_data["achievements"]:.4f}% | {music.id}. {music.title} | {DIFFICULTY_NAME[achievement_data["level_index"]]} {music.ds[achievement_data["level_index"]]}')
            if achievement_data['fc']:
                messages.append(f' | {COMBO_RANK[combo_rank.index(achievement_data["fc"])]}')
            if achievement_data['fs']:
                messages.append(f' {SYNC_RANK[sync_rank.index(achievement_data["fs"])]}')
            messages.append('\n')
    messages.append(f'第{page + 1}页，共{pages}页')
    if pages > 1:
        messages.append(f'，发送“{ds or level}分数列表 <页码>{" " + user if user is not None else ""}”查看其他页')

    await level_achievement.finish(
        MessageSegment.image(image_to_bytesio(text_to_image(''.join(messages)))))


@rating_ranking.handle()
async def rating_ranking_func(bot: Bot, event: MessageEvent, message: Message = CommandArg()) -> None:
    user: str = message.extract_plain_text().strip()
    payload, nickname = await get_payload_and_nickname(bot, event, message, user)
    data: dict[str, Any] | str = await get_player_data('best', payload, event.user_id)  # 先查一下b50来获取用户名和rating
    if isinstance(data, str):
        await rating_ranking.finish(data, reply_message=True)
    username: str = data['username']
    rating: int = data['rating']
    ranking_data: list[dict[str, Any]] | str = await get_rating_ranking_data()
    if isinstance(ranking_data, str):
        await rating_ranking.finish(ranking_data, reply_message=True)

    ranking_data.sort(key=lambda x: x['ra'])
    count: int = len(ranking_data)
    ranking: int = bisect_right(ranking_data, rating, key=lambda x: x['ra'])  # 实际上是倒数第几
    await rating_ranking.finish(f'{username}的rating为{rating}\n'
                                f'排名为{count - ranking + 1} / {count}\n'
                                f'超越了{ranking / count:.2%}的玩家哦\n'
                                f'在水鱼网上传了成绩的用户中\n'
                                # f'rating排名第1的玩家是{ranking_data[0]["username"]}，rating为{ranking_data[0]["ra"]}\n'
                                # f'rating排名第2的玩家是{ranking_data[1]["username"]}，rating为{ranking_data[1]["ra"]}\n'
                                # f'rating排名第3的玩家是{ranking_data[2]["username"]}，rating为{ranking_data[2]["ra"]}\n'
                                f'平均rating为{sum(x["ra"] for x in ranking_data) / count:.2f}\n'
                                f'第一四分位数为{ranking_data[round((count - 1) * 3/4)]["ra"]}\n'
                                f'中位数为{ranking_data[round(count / 2)]["ra"]}\n'
                                f'第三四分位数为{ranking_data[round((count - 1) / 4)]["ra"]}',
                                at_sender=True
                                )


@query_chart.handle()
async def query_chart_func(group: tuple[str | None, str] = RegexGroup()) -> None:
    level_han, music_id = group
    music: Music | None = Mai.music_list.by_id(music_id)
    if music is None:
        await query_chart.finish(f'没有找到id为{music_id}的乐曲呢……')
    if level_han is not None:
        diff_index: int = '绿黄红紫白'.index(level_han)
        await query_chart.finish(await chart_info(music, diff_index))
    else:
        await query_chart.finish(await music_info(music))


@search_music_by_title.handle()
async def search_music_by_title_func(message: Message = CommandArg()) -> None:
    name: str = message.extract_plain_text()
    if not name:
        await search_music_by_title.finish('请输入要查询的乐曲。')
    result: MusicList = Mai.music_list.by_title(name)
    if not result:
        await search_music_by_title.finish(f'没有找到标题中含有“{name}”的乐曲呢……\n试试别名查歌（命令为“...是什么歌”）吧~')
    if len(result) == 1:
        (music, ) = result
        await search_music_by_title.finish(await music_info(music))
    if len(result) <= 48:
        result.sort(key=lambda music: int(music.id))
        await search_music_by_title.finish(f'查询到{len(result)}首乐曲：\n'
                                           + '\n'.join(music_info_compact(music) for music in result))
    await search_music_by_title.finish(f'结果过多（{len(result)}条），请缩小查询范围。')


@search_music_by_alias.handle()
async def search_music_by_alias_func(group: tuple[str] = RegexGroup()) -> None:
    (alias, ) = group
    result: MusicList = Mai.music_list.by_alias(alias)
    if not result:
        await search_music_by_alias.finish('没有找到这样的乐曲。')
    if len(result) == 1:
        (music, ) = result
        await search_music_by_alias.finish(await music_info(music))
    if len(result) <= 48:
        await search_music_by_alias.finish(f'查询到{len(result)}首乐曲：\n'
                                           + '\n'.join(music_info_compact(music) for music in result))
    await search_music_by_alias.finish(f'结果过多（{len(result)}条），请缩小查询范围。')


@search_music_by_inner.handle()
async def search_music_by_inner_func(message: Message = CommandArg()) -> None:
    args: list[str] = message.extract_plain_text().strip().split()
    try:
        page: int = 0
        if len(args) == 1:
            ds: float | tuple[float, float] = float(args[0])
            assert math.isfinite(ds), ValueError
        elif len(args) == 2:
            ds = (float(args[0]), float(args[1]))
            assert math.isfinite(ds[0]) and math.isfinite(ds[1]), ValueError
        else:
            ds = (float(args[0]), float(args[1]))
            page = int(args[2]) - 1
            assert math.isfinite(ds[0]) and math.isfinite(ds[1]), ValueError
    except ValueError:
        await search_music_by_inner.finish(search_music_by_inner_help_text)

    result: list[tuple[Music, int]] = Mai.music_list.by_ds(ds)
    if not result:
        await search_music_by_inner.finish('没有找到符合条件的乐曲。', reply_message=True)

    pages: int = math.ceil(len(result) / plugin_config.songs_per_page)
    page = max(min(page, pages - 1), 0)
    messages: list[str] = []
    i: int = 0
    for i, (music, diff_index) in enumerate(sorted(result, key=lambda i: (i[0].ds[i[1]], i[0].id))):
        if page * plugin_config.songs_per_page <= i < (page + 1) * plugin_config.songs_per_page:
            messages.append(music_info_with_diff_compact(music, diff_index))
    if pages > 1:
        if isinstance(ds, float):
            messages.append(f'第{page + 1}页，共{pages}页，发送“定数查歌 {ds} {ds} <页码>”查看其他页')
        else:
            messages.append(f'第{page + 1}页，共{pages}页，发送“定数查歌 {ds[0]} {ds[1]} <页码>”查看其他页')
    else:
        messages.append(f'第{page + 1}页，共{pages}页')
    await search_music_by_tempo.finish(MessageSegment.image(image_to_bytesio(text_to_image('\n'.join(messages)))))


@search_music_by_tempo.handle()
async def search_music_by_tempo_func(message: Message = CommandArg()) -> None:
    args: list[str] = message.extract_plain_text().strip().split()
    try:
        page: int = 0
        if len(args) == 1:
            bpm: int | tuple[int, int] = int(args[0])
        elif len(args) == 2:
            bpm = (int(args[0]), int(args[1]))
        else:
            bpm = (int(args[0]), int(args[1]))
            page = int(args[2]) - 1
    except ValueError:
        await search_music_by_tempo.finish(search_music_by_tempo_help_text, reply_message=True)

    result: MusicList = Mai.music_list.by_bpm(bpm)
    if not result:
        await search_music_by_tempo.finish(f'没有找到符合条件的乐曲。', reply_message=True)

    pages: int = math.ceil(len(result) / plugin_config.songs_per_page)
    page = max(min(page, pages - 1), 0)
    messages: list[str] = []
    for i, music in enumerate(sorted(result, key=lambda i: (i.bpm, i.ds, i.id))):
        if page * plugin_config.songs_per_page <= i < (page + 1) * plugin_config.songs_per_page:
            messages.append(f'No. {i+1} | {music.id}. {music.title} | {music.bpm}bpm')
    if pages > 1:
        if isinstance(bpm, int):
            messages.append(f'第{page + 1}页，共{pages}页，发送“bpm查歌 {bpm} {bpm} <页码>”查看其他页')
        else:
            messages.append(f'第{page + 1}页，共{pages}页，发送“bpm查歌 {bpm[0]} {bpm[1]} <页码>”查看其他页')
    else:
        messages.append(f'第{page + 1}页，共{pages}页')
    await search_music_by_tempo.finish(MessageSegment.image(image_to_bytesio(text_to_image('\n'.join(messages)))))


@search_music_by_artist.handle()
async def search_music_by_artist_func(message: Message = CommandArg()) -> None:
    message_plain_text: str = message.extract_plain_text().strip()
    if not message_plain_text:
        await search_music_by_artist.finish(search_music_by_artist_help_text, reply_message=True)

    args: list[str] = message_plain_text.rsplit(maxsplit=1)
    name: str = message_plain_text
    page: int = 0
    if len(args) == 2 and args[1].isdigit():
        name: str = args[0]
        page = int(args[1]) - 1

    results: MusicList = Mai.music_list.by_artist(name)
    if not results:
        await search_music_by_artist.finish(f'没有找到艺术家为“{name}”的乐曲呢……', reply_message=True)

    pages: int = math.ceil(len(results) / plugin_config.songs_per_page)
    page = max(min(page, pages - 1), 0)
    messages: list[str] = []
    for i, music in enumerate(results):
        if page * plugin_config.songs_per_page <= i < (page + 1) * plugin_config.songs_per_page:
            messages.append(f'No. {i+1} | {music.id}. {music.title} | {music.artist}')
    if pages > 1:
        messages.append(f'第{page + 1}页，共{pages}页，发送“曲师查歌 {name} <页码>”查看其他页')
    else:
        messages.append(f'第{page + 1}页，共{pages}页')
    await search_music_by_artist.finish(MessageSegment.image(image_to_bytesio(text_to_image('\n'.join(messages)))))


@search_music_by_charter.handle()
async def search_music_by_charter_func(message: Message = CommandArg()) -> None:
    message_plain_text: str = message.extract_plain_text().strip()
    if not message_plain_text:
        await search_music_by_artist.finish(search_music_by_charter_help_text, reply_message=True)

    args: list[str] = message_plain_text.rsplit(maxsplit=1)
    name: str = message_plain_text
    page: int = 0
    if len(args) == 2 and args[1].isdigit():
        name: str = args[0]
        page = int(args[1]) - 1

    # result: MusicList = Mai.music_list.filter(charter_search=name)
    result: list[tuple[Music, int]] = Mai.music_list.by_charter(name)
    if not result:
        await search_music_by_charter.finish(f'没有找到谱师为“{name}”的谱面呢……', reply_message=True)

    pages: int = math.ceil(len(result) / plugin_config.songs_per_page)
    page = max(min(page, pages - 1), 0)
    messages: list[str] = []
    for i, (music, diff_index) in enumerate(result):
        if page * plugin_config.songs_per_page <= i < (page + 1) * plugin_config.songs_per_page:
            # diff_charter = zip([DIFFICULTY_NAME[i] for i in music.diff], [music.charts[d].charter for d in music.diff])
            # messages.append(f'No. {i+1} | {music.id}. {music.title} | {" | ".join([f"{difficulty_name} {charter}" for difficulty_name, charter in diff_charter])}')
            messages.append(f'No. {i+1} | {music.id}. {music.title} | {DIFFICULTY_NAME[diff_index]} {music.ds[diff_index]} {music.charts[diff_index].charter}')
    if pages > 1:
        messages.append(f'第{page + 1}页，共{pages}页，发送“谱师查歌 {name} <页码>”查看其他页')
    else:
        messages.append(f'第{page + 1}页，共{pages}页')
    await search_music_by_charter.finish(MessageSegment.image(image_to_bytesio(text_to_image('\n'.join(messages)))))


@chart_stats.handle()
async def chart_stats_func(message: Message = CommandArg()) -> None:
    plain_text: str = message.extract_plain_text().strip()
    diff_index: int = '绿黄红紫白'.find(plain_text[0])  # 未指定则为-1
    if diff_index == -1:
        name = plain_text
    else:
        name = plain_text[1:]

    matched_music: MusicList = Mai.music_list.by_name(name)
    if not matched_music:
        await music_score.finish(f'没有找到id/标题/别名为“{name}”的乐曲。')
    if 1 < len(matched_music) <= 25:
        await music_score.finish(f'“{name}”匹配{len(matched_music)}首乐曲：\n'
                                 + '\n'.join(music_info_compact(music) for music in matched_music)
                                 + '\n请发送乐曲的id以确定查询的乐曲。')
    elif len(matched_music) > 25:
        await music_score.finish(f'“{name}”匹配{len(matched_music)}首乐曲：\n'
                                 + '请发送乐曲的id以确定查询的乐曲。')

    (music,) = matched_music
    if diff_index == -1:
        diff_index = music.diff_num - 1
    diff_index = min(diff_index, music.diff_num - 1)
    stats: ChartStats = music.charts[diff_index].stats
    if not stats:
        await chart_stats.finish('该乐曲还没有统计信息', reply_message=True)
    # await chart_stats.finish(MessageSegment.image(image_to_bytesio(music_global_data(music, diff_index)))
    #                          + (f'游玩次数：{round(stats.count)}\n'
    #                             f'拟合难度：{stats.fit_diff:.2f}\n'
    #                             f'平均达成率：{stats.avg_achievement:.4f}%\n'
    #                             f'平均 DX 分数：{stats.avg_dx_score:.2f}\n'
    #                             f'谱面成绩标准差：{stats.std_dev:.4f}'),
    #                          at_sender=True)
    await chart_stats.finish(
        MessageSegment.image(image_to_bytesio(chart_stats_text(music, diff_index))))


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
    music.aliases[alias] = AliasInfo.from_json(info)
    async with aiofiles.open(plugin_config.data_path / 'aliases.json', 'r', encoding='utf-8') as fp:
        aliases = json.loads(await fp.read())
    if id not in aliases:
        aliases[id] = {'title': music.title, 'aliases': {}}
    aliases[id]['aliases'][alias] = info
    async with aiofiles.open(plugin_config.data_path / 'aliases.json', 'w', encoding='utf-8') as fp:
        await fp.write(json.dumps(aliases, ensure_ascii=False, indent=4))
    await add_alias.finish(f'已为 {id}. {music.title} 添加别名“{alias}”')


@delete_alias.handle()
async def delete_alias_func(bot: Bot, event: GroupMessageEvent, message: Message = CommandArg()) -> None:
    try:
        id, alias = message.extract_plain_text().split(maxsplit=1)
    except ValueError:
        await add_alias.finish('命令格式：\n删除别名 <乐曲id> <乐曲别名>')
    music: Music | None = Mai.music_list.by_id(id)
    if music is None:
        await delete_alias.finish(f'没有id为{id}的乐曲。')
    if alias not in music.aliases:
        await delete_alias.finish(f'该别名不存在。')
    if music.aliases[alias].group != event.group_id:
        await delete_alias.finish(f'别名“{alias}”由非本群的成员添加，不可在本群删除。')
    if (music.aliases[alias].role in ('owner', 'admin')
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
async def query_alias_func(message: Message = CommandArg()) -> None:
    name: str = message.extract_plain_text()
    matched_music: MusicList = Mai.music_list.by_name(name)
    if not matched_music:
        await music_score.finish(f'没有找到id/标题/别名为{name}的乐曲。')
    if len(matched_music) > 1:
        await music_score.finish(f'“{name}”匹配{len(matched_music)}首乐曲：\n'
                                 + '\n'.join(music_info_compact(music) for music in matched_music)
                                 + '\n请发送乐曲的id以确定查询的乐曲。')
    (music,) = matched_music
    if not music.aliases:
        await query_alias.finish(f'{music.id}. {music.title}暂无别名。')
    result: list[str] = [f'{music.id}. {music.title}的别名共{len(music.aliases)}个：']
    for i, (alias, info) in enumerate(music.aliases.items()):
        # if info['group'] != event.group_id:
        #     info_str: str = f'{info["card"] or info["nickname"]} ({info["qqid"]})'
        # else:
        #     info_str = '非本群的成员'
        result.append(f'{i+1}. {alias}  # 由{info.card or info.nickname} ({info.qqid}) 于{strftime(info.time)}设置')
    await query_alias.finish('\n'.join(result))


@score_line.handle()
async def score_line_func(message: Message = CommandArg()):
    regex = r'(绿|黄|红|紫|白)(id)?([0-9]+)'
    argv: list[str] = message.extract_plain_text().strip().split()
    if len(argv) == 1 and argv[0] == '帮助':
        await score_line.send(MessageSegment.image(image_to_bytesio(text_to_image(query_score_help_text))))
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


@guess_music_start.handle()
async def guess_music_start_func(bot: Bot, event: MessageEvent) -> None:
    if is_now_playing_guess_music(bot, event):
        await guess_music_start.finish('该群已有正在进行的猜歌', reply_message=True)
    guess = Guess()
    guesses[get_event_id(bot, event)] = guess
    await guess_music_start.send(
        '我将从热门乐曲中选择一首乐曲，每隔8秒描述它的特征\n'
        '请输入乐曲的 id 或 标题 或 别名（不区分大小写）进行猜歌\n'
        'DX乐谱和标准乐谱视为两首乐曲\n'
        '猜歌时查歌等其他命令依然可用'
    )
    await guess_music_loop(bot, event, guess)


@guess_music_solve.handle()
async def guess_music_solve_func(bot: Bot, event: MessageEvent, message: str = EventPlainText()) -> None:
    message = message.strip()
    guess: Guess = guesses[get_event_id(bot, event)]
    answer: Music = guess.music
    matched_musics: MusicList = Mai.music_list.by_alias(message)
    if answer.id == message or (len(matched_musics) == 1 and answer.id == matched_musics[0].id):
        guess.finished = True
        del guesses[get_event_id(bot, event)]
        await guess_music_solve.finish('猜对了，答案是：' + await music_info(answer), reply_message=True)
    elif 2 <= len(matched_musics) <= 10:
        await guess_music_solve.finish(f'“{message}”匹配{len(matched_musics)}首乐曲：\n'
                                       + '\n'.join(music_info_compact(music) for music in matched_musics)
                                       + '\n请发送乐曲的id以确定猜测的乐曲。')


async def guess_music_loop(bot: Bot, event: MessageEvent, guess: Guess) -> None:
    if guess.round == 0:
        await asyncio.sleep(4)
    else:
        await asyncio.sleep(8)
    if guess.finished:
        return

    if guess.round < guess.rounds:
        await guess_music_start.send(await guess.give_hint())
    if guess.round == guess.rounds:
        await give_answer(bot, event, guess)
    else:
        await guess_music_loop(bot, event, guess)


async def give_answer(bot: Bot, event: MessageEvent, guess: Guess) -> None:
    await asyncio.sleep(30)
    if guess.finished:
        return
    guess.finished = True
    del guesses[get_event_id(bot, event)]
    await guess_music_start.finish('答案是：' + await music_info(guess.music))


@set_privacy.handle()
async def set_privacy_func(event: MessageEvent, message: str = EventPlainText()) -> None:
    if any(x in message for x in ('禁止', '拒绝', '不允许')):
        enable: bool = False
    elif any(x in message for x in ('同意', '允许')):
        enable = True
    else:
        await set_privacy.finish()

    privacy_set_privacy(event.user_id, enable)
    prompt: str = '允许' if enable else '禁止'
    await set_privacy.finish(f'已{prompt}其他人查询您的成绩')
