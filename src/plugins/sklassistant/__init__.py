import sys

sys.path.append("src/arknights-game-model")  # NOQA

import asyncio
from typing import Any

import httpx
from arknights_game_model.game_data import game_data
from arknights_game_model.item_info_model import ItemInfo, ItemInfoList
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_cultivate_player import \
    HttpsZonaiSklandComApiV1GameCultivatePlayer as CultivatePlayer
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_binding import \
    HttpsZonaiSklandComApiV1GamePlayerBinding as PlayerBinding
from arknights_game_model.skland.https_zonai_skland_com_api_v1_search_user import \
    HttpsZonaiSklandComApiV1SearchUser as SearchUser
from nonebot import MatcherGroup, get_driver, logger, require
from nonebot.adapters.onebot.v11 import Message, MessageEvent, MessageSegment
from nonebot.drivers import Driver
from nonebot.exception import MatcherException
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText, RegexGroup
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .app import app
from .assistant import 森空岛实时数据分析, 森空岛干员阵容查询
from .config import plugin_config
from .image import image_to_bytesio, text_to_image
from .manager import tokens
from .skland import TOKEN_LENGTH, SKLand, SKLandError, api_v1_search_user_url, attendance_and_send_email, login_headers
from .utils import get_qq_mail_address, is_base64

require('nonebot_plugin_apscheduler')

from nonebot_plugin_apscheduler import scheduler  # NOQA: E402

driver: Driver = get_driver()
default_command_start: str = tuple(driver.config.command_start)[0]

token_str = f"""
【如何绑定森空岛 token】
方法一：点击下面链接，按照提示操作
http://{plugin_config.skl_server_host}:{plugin_config.skl_quart_port}/BioBot/plugins/sklassistant/
方法二：点击上面链接查看如何获取森空岛 token，
然后添加 bot 为好友，私聊发送“{default_command_start}绑定森空岛token <token>”
# 为了您的账号安全，请不要在群聊中直接发送 token！
""".strip()

no_token_str = f"""未绑定森空岛 token，请先绑定森空岛 token。\n\n{token_str}"""

help_str: str = f'''
{token_str}

【可用命令】
- {default_command_start}绑定森空岛token <token>    # 绑定森空岛 token

- {default_command_start}(关闭|开启)森空岛自动签到    # 关闭/开启森空岛自动签到

- {default_command_start}森空岛小秘书 [<uid>]    # 森空岛实时数据分析
- {default_command_start}森空岛小秘书 <森空岛用户名|森空岛 ID> <uid>    # 查别人的成分

- {default_command_start}森空岛干员阵容查询 [<uid>]    # 查询已有干员
- {default_command_start}未拥有干员 [<uid>]    # 查询未拥有干员

- {default_command_start}我的仓库  # 查询仓库材料
- {default_command_start}已消耗材料 [<uid>]    # 查询养成总消耗
- {default_command_start}满练还差多少 [<uid>]    # 查询满练差多少材料

# <uid> 为一串数字，可在游戏主界面昵称下方找到。
# <uid> 为可选参数。若不指定 <uid>，则查询官网绑定的默认角色。
'''.strip()

# - {default_command_start}解绑森空岛token <token>    # 解绑一个森空岛 token
# - {default_command_start}解绑所有森空岛token    # 解绑所有森空岛 token

__plugin_meta__ = PluginMetadata(
    name='森空岛小助手',
    description='明日方舟森空岛工具，提供自动签到、干员查询、仓库查询等各种实用功能。',
    usage=help_str,
)

matcher_group = MatcherGroup(priority=1, block=False)
bind_skl_token_command = matcher_group.on_command('绑定森空岛token')
bind_skl_token_regex = matcher_group.on_regex(r'{"code":0,"data":{"content":"(.+)"},"msg":".+"}')
# delete_skl_token = matcher_group.on_command('删除森空岛token', aliases={'解绑森空岛token'})
# delete_all_skl_token = matcher_group.on_command('解绑所有森空岛token', aliases={'解绑全部森空岛token', "删除全部森空岛token", "删除所有森空岛token"})

skl_auto_attendance = matcher_group.on_keyword({'森空岛自动签到'})
skl_attendance_all = matcher_group.on_command('森空岛签到全部', permission=SUPERUSER)

skl_assistant = matcher_group.on_command('森空岛小秘书', aliases={'森空岛助手', '森空岛小助手'})

skl_query = matcher_group.on_command('森空岛查询', aliases={'森空岛干员阵容查询'})
skl_missing_characters = matcher_group.on_command("未拥有干员")

skl_my_depot = matcher_group.on_command('我的仓库', aliases={'已有材料', '仓库材料'})
skl_consumed_items = matcher_group.on_command('已消耗材料', aliases={'养成总消耗'})
skl_missing_items = matcher_group.on_command('满练需要材料', aliases={'满练差多少材料', "满练还差多少"})

skl_binding = matcher_group.on_command('森空岛用户绑定角色')


@scheduler.scheduled_job('cron', hour=0)
# @driver.on_startup
async def skl_sign_in_all() -> list[dict[str, Any] | BaseException]:
    logger.info('开始森空岛自动签到')
    tasks = [attendance_and_send_email(item['token'], item['remind'], item['email'])
             for item in tokens if item['enabled']]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        logger.info(repr(result))
    return results


# @driver.on_startup
async def run_app() -> None:
    asyncio.create_task(app.run_task(plugin_config.skl_quart_host, plugin_config.skl_quart_port))


async def get_character(*, matcher: Matcher, skland: SKLand, qq: int, uid: str | None, app_code: str = "arknights") -> dict[str, Any]:
    """
    uid 为数字且成功找到角色则返回该角色，否则返回官网绑定的默认角色。
    未找到 uid 对应的角色或者未绑定任何角色直接结束对话。
    任何一个账号登录失败则抛出异常。
    只会返回 `dict[str, Any]`。
    """
    # 处理用户输入
    if uid is not None and not uid.strip().isdigit():
        uid = None

    # 检查是否绑定了森空岛 token
    token_list = tokens.filter(qq=qq)
    if not token_list:
        await matcher.finish(no_token_str)

    for item in token_list:
        token = item["token"]
        # 尝试登录，如果登录失败则直接抛出异常
        await skland.login_by_token(token)
        player_binding = await skland.player_binding()
        character = skland.get_character(player_binding, uid, app_code)
        if character is not None:
            return character
    else:
        await matcher.finish("该账号未绑定该角色。")


@bind_skl_token_command.handle()
@bind_skl_token_regex.handle()
async def bind_skl_token_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg(), group: tuple[str] = RegexGroup()) -> None:
    # TODO: 在群聊中发送消息时撤回消息
    if isinstance(matcher, bind_skl_token_command):
        token: str = message.extract_plain_text().strip()
    else:
        token = group[0].strip()

    if not token:
        await matcher.finish(help_str)

    if not (len(token) == TOKEN_LENGTH and is_base64(token)):
        await matcher.finish('token 格式错误，请确认 token 不带引号。如需帮助，请发送“绑定森空岛token”。')

    if tokens.has_token(token):
        await matcher.finish('token 已存在。')

    try:
        await SKLand().login_by_token(token)
    except Exception as e:
        await matcher.finish(f'绑定森空岛 token 失败：{e}')

    tokens.add_item(event.user_id, get_qq_mail_address(event.user_id), token)
    await matcher.send('成功绑定森空岛 token。立即进行一次签到。\n'
                       '已为您开启自动签到和邮件提醒，以后将于每日 00:00 签到。\n'
                       '如暂时不需要开启，请发送“关闭森空岛自动签到”。')

    result: dict[str, Any] = await attendance_and_send_email(token, True, get_qq_mail_address(event.user_id))
    await matcher.finish(result['msg'])


# @delete_skl_token.handle()
# async def delete_skl_token_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
#     token: str = message.extract_plain_text().strip()
#     if not token:
#         await delete_skl_token.finish(f'请在命令后面跟上要解绑的 token。如果要解绑所有 token，请发送“{default_command_start}解绑所有森空岛token”。')

#     if len(token) != TOKEN_LENGTH or not is_base64(token):
#         await delete_skl_token.finish('token 格式错误，请确认 token 不带引号。如需帮助，请发送“绑定森空岛token”。')

#     if not tokens.filter(qq=event.user_id, token=token):
#         await delete_skl_token.finish('未找到该 token。')

#     tokens.remove_item('token', token)

#     await delete_skl_token.finish('成功删除森空岛token。')


# @delete_all_skl_token.handle()
# async def delete_all_skl_token_func(matcher: Matcher, event: MessageEvent) -> None:
#     if not tokens.filter(qq=event.user_id):
#         await delete_all_skl_token.finish("还没有绑定过森空岛 token。")

#     tokens.remove_item('qq', event.user_id)

#     await delete_all_skl_token.finish('成功解绑所有森空岛token。')


@skl_auto_attendance.handle()
async def skl_auto_attendance_func(event: MessageEvent, message: str = EventPlainText()) -> None:
    if '关闭' in message:
        enable: bool = False
    elif '开启' in message:
        enable = True
    else:
        await skl_auto_attendance.finish()

    if not tokens.filter(qq=event.user_id):
        await skl_auto_attendance.finish(no_token_str)

    tokens.set_enable_state('qq', event.user_id, enable)

    if enable:
        await skl_auto_attendance.send('已开启森空岛自动签到。立即进行一次签到。以后将于每日00:00签到。')
        tasks = (attendance_and_send_email(item['token'], True, item['email'])
                 for item in tokens if item['qq'] == event.user_id)
        results: list[dict[str, Any] | BaseException] = await asyncio.gather(*tasks, return_exceptions=True)
        await skl_auto_attendance.finish(
            '\n'.join(result['msg'] if isinstance(result, dict) else repr(result)
                      for result in results)
        )
    else:
        await skl_auto_attendance.finish('已关闭森空岛自动签到。')


@skl_attendance_all.handle()
async def skl_attendance_all_func() -> None:
    results = await skl_sign_in_all()
    await skl_attendance_all.finish('\n'.join(repr(result) for result in results))


@skl_assistant.handle()
@skl_query.handle()
async def skl_assistant_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    uid: str | None = message.extract_plain_text().strip()
    if not uid.isdigit():
        uid = None

    token_list = tokens.filter(qq=event.user_id)
    if not token_list:
        await skl_assistant.finish(no_token_str)

    exception = None
    for item in token_list:
        token = item['token']
        try:
            if type(matcher) is skl_assistant:
                result: str = await 森空岛实时数据分析(token, uid)
            else:
                result = await 森空岛干员阵容查询(token, uid)
        except Exception as e:
            exception = e
        else:
            if len(result) > 512:
                await skl_assistant.send(MessageSegment.image(image_to_bytesio(text_to_image(result))))
            else:
                await skl_assistant.send(result)

    if isinstance(exception, SKLandError):
        await skl_assistant.send(str(exception))
        raise exception
    elif isinstance(exception, Exception):
        await skl_assistant.send(repr(exception))
        raise exception


@skl_missing_characters.handle()
@skl_my_depot.handle()
@skl_consumed_items.handle()
@skl_missing_items.handle()
@skl_binding.handle()
async def _(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    try:
        if isinstance(matcher, skl_missing_characters):
            await skl_missing_characters_func(matcher, event, message)
        elif isinstance(matcher, skl_my_depot):
            await skl_my_depot_func(matcher, event, message)
        elif isinstance(matcher, skl_consumed_items):
            await skl_consumed_or_missing_items_func(matcher, event, message)
        elif isinstance(matcher, skl_missing_items):
            await skl_consumed_or_missing_items_func(matcher, event, message)
        elif isinstance(matcher, skl_binding):
            await skl_binding_func(matcher, event, message)

    except SKLandError as e:
        await matcher.send(str(e))
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


async def skl_missing_characters_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    skland = SKLand()
    binding_character = await get_character(matcher=matcher,
                                            skland=skland,
                                            qq=event.user_id,
                                            uid=message.extract_plain_text().strip(),
                                            app_code="arknights")

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj)

    missing_character_list = []
    for character_id, character in game_data.characters.items():
        for skl_character in cultivate_player.data.characters:
            if skl_character.id == character_id:
                break
        else:
            missing_character_list.append(character)

    lines: list[str] = []

    lines.append(f"{binding_character["channelName"]}账号 {binding_character["nickName"]}（{binding_character["uid"]}）")
    lines.append("________________")
    lines.append("")
    lines.append("/- 未拥有干员 -/")
    lines.append("")
    lines.append("、".join(character.name for character in missing_character_list))
    lines.append("")
    lines.append("________________")
    lines.append("# Generated by BioBot")
    lines.append("# Made by bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    await matcher.send("\n".join(lines))


async def skl_my_depot_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    skland = SKLand()
    binding_character = await get_character(matcher=matcher,
                                            skland=skland,
                                            qq=event.user_id,
                                            uid=message.extract_plain_text().strip(),
                                            app_code="arknights")

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj)

    item_info_list: ItemInfoList = ItemInfoList()
    for item in cultivate_player.data.items:
        item_info_list.append(ItemInfo(item_id=item.id, count=item.count))
    item_info_list.sort_in_place_by_sort_id()

    yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

    lines: list[str] = []

    lines.append(f"{binding_character["channelName"]}账号 {binding_character["nickName"]}（{binding_character["uid"]}）")
    lines.append("________________")
    lines.append("")
    lines.append("/- 仓库材料 -/")
    lines.append("")
    lines.extend(str(item_info_list).split())
    lines.append("")
    lines.append(f"相当于 {yituliu_item_value:.2f} 理智")
    lines.append("")
    lines.append("________________")
    lines.append("# 物品价值数据来自 明日方舟一图流 - 物品价值表")
    lines.append("https://ark.yituliu.cn/material/value")
    lines.append("")
    lines.append("# Generated by BioBot")
    lines.append("# Made by bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    await matcher.send("\n".join(lines))


def get_consumed_item_info_list(cultivate_player: CultivatePlayer) -> ItemInfoList:
    item_info_list: ItemInfoList = ItemInfoList()
    for skl_character in cultivate_player.data.characters:
        character = game_data.characters.by_id(skl_character.id)
        item_info_list.extend(character.养成消耗(
            目标精英化阶段=skl_character.evolve_phase,
            目标等级=skl_character.level,
            目标技能专精等级列表=[skill.level for skill in skl_character.skills],
            目标模组等级字典={equip.id: equip.level for equip in skl_character.equips}
        ))
    item_info_list.combine_in_place()
    item_info_list.sort_in_place_by_sort_id()
    return item_info_list


def get_missing_item_info_list(cultivate_player: CultivatePlayer) -> ItemInfoList:
    item_info_list: ItemInfoList = ItemInfoList()
    owned_character_id_set = {character.id for character in cultivate_player.data.characters}
    not_owned_character_id_set = game_data.characters.keys() - owned_character_id_set
    for skl_character in cultivate_player.data.characters:
        character = game_data.characters.by_id(skl_character.id)
        item_info_list.extend(character.养成消耗(
            初始精英化阶段=skl_character.evolve_phase,
            初始等级=skl_character.level,
            初始技能专精等级列表=[skill.level for skill in skl_character.skills],
            初始模组等级字典={equip.id: equip.level for equip in skl_character.equips}
        ))
    for character_id in not_owned_character_id_set:
        character = game_data.characters.by_id(character_id)
        item_info_list.extend(character.养成消耗())
    item_info_list.combine_in_place()
    item_info_list.sort_in_place_by_sort_id()
    return item_info_list


async def skl_consumed_or_missing_items_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    skland = SKLand()
    binding_character = await get_character(matcher=matcher,
                                            skland=skland,
                                            qq=event.user_id,
                                            uid=message.extract_plain_text().strip(),
                                            app_code="arknights")

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj)

    if isinstance(matcher, skl_consumed_items):
        item_info_list = get_consumed_item_info_list(cultivate_player)
        title = "养成总消耗"
    else:
        item_info_list = get_missing_item_info_list(cultivate_player)
        title = "距离满练还差"

    yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

    lines: list[str] = []

    lines.append(f"{binding_character["channelName"]}账号 {binding_character["nickName"]}（{binding_character["uid"]}）")
    lines.append("________________")
    lines.append("")
    lines.append(f"/- {title} -/")
    lines.append("")
    lines.extend(str(item_info_list).split())
    lines.append("")
    lines.append(f"相当于 {yituliu_item_value:.2f} 理智")
    lines.append("")
    lines.append("________________")
    lines.append("# 物品价值数据来自 明日方舟一图流 - 物品价值表")
    lines.append("https://ark.yituliu.cn/material/value")
    lines.append("")
    lines.append("# Generated by BioBot")
    lines.append("# Made by bilibili@Bio-Hazard")
    lines.append("https://space.bilibili.com/37179776")

    await matcher.send("\n".join(lines))


async def skl_binding_func(matcher: Matcher, event: MessageEvent, message: Message = CommandArg()) -> None:
    # 检查是否绑定了森空岛 token
    token_list = tokens.filter(qq=event.user_id)
    if not token_list:
        await matcher.finish(no_token_str)

    skland = SKLand()
    id_or_name: str = message.extract_plain_text().strip()
    if not id_or_name:
        user_id = None
    elif id_or_name.isdigit():
        user_id = id_or_name
    else:
        token = token_list[0]['token']
        await skland.login_by_token(token)

        url = httpx.URL(api_v1_search_user_url).copy_merge_params(dict(keyword=id_or_name, pageSize=20))
        search_result_obj = await skland._request("GET", str(url), login_headers, json=None, sign=True)
        search_user = SearchUser.model_validate(search_result_obj)
        if search_user.data.list:
            user_id = search_user.data.list[0].user.id
        else:
            await matcher.finish(f'未找到用户 {id_or_name}。')

    # 如果查自己的（user_id is None），则尝试所有 token，否则只使用第一个 token
    if user_id is not None:
        token_list = token_list[:1]

    for item in token_list:
        token = item["token"]

        # 尝试登录
        if getattr(skland, "token", None) != token:
            await skland.login_by_token(token)

        player_binding_obj = await skland.player_binding(uid=user_id)
        player_binding = PlayerBinding.model_validate(player_binding_obj)

        lines: list[str] = []
        lines.append("用户绑定列表")
        lines.append("________________")
        for app_info in player_binding.data.list:
            lines.append("")
            lines.append(f"/- {app_info.app_code}（{app_info.app_name}） -/")
            lines.append("")
            for binding_character in app_info.binding_list:
                lines.append(f"{binding_character.channel_name}账号 {binding_character.nick_name}（{binding_character.uid}{"，默认" if binding_character.is_default else ""}）")
        lines.append("")
        lines.append("________________")
        lines.append("# Generated by BioBot")
        lines.append("# Made by bilibili@Bio-Hazard")
        lines.append("https://space.bilibili.com/37179776")

        await matcher.send("\n".join(lines))
