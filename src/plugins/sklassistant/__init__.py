# ruff: noqa: E402
"""
TODO: 材料归蓝
TODO: 菲亚梅塔心情预测
TODO: 给干员排序
TODO: 如果账号很久没登录，则/api/v1/game/player/info 中 chars 的模组可能不包含该干员的全部模组。
"""

from nonebot import require

require("nonebot_plugin_apscheduler")
require("nonebot_plugin_orm")

import asyncio
from datetime import datetime
from itertools import accumulate
from typing import Annotated, Any

import httpx
from arknights_game_model.game_data import game_data
from arknights_game_model.item_info_model import ItemInfo, ItemInfoList
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_cultivate_player import (
    HttpsZonaiSklandComApiV1GameCultivatePlayer as CultivatePlayer,
)
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_binding import (
    HttpsZonaiSklandComApiV1GamePlayerBinding as PlayerBinding,
)
from arknights_game_model.skland.https_zonai_skland_com_api_v1_game_player_info import (
    HttpsZonaiSklandComApiV1GamePlayerInfo as PlayerInfo,
)
from arknights_game_model.skland.https_zonai_skland_com_api_v1_search_user import (
    HttpsZonaiSklandComApiV1SearchUser as SearchUser,
)
from nonebot import MatcherGroup, get_driver, logger
from nonebot.adapters.onebot.v11 import (
    Bot,
    GroupMessageEvent,
    Message,
    MessageEvent,
    MessageSegment,
)
from nonebot.drivers import Driver
from nonebot.exception import MatcherException, ParserExit
from nonebot.matcher import Matcher
from nonebot.params import CommandArg, EventPlainText, RegexGroup, ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import ArgumentParser, Namespace
from nonebot_plugin_apscheduler import scheduler

from .app import on_startup
from .assistant import (
    CST,
    divide,
    skl_assistant_func,
    森空岛实时数据分析,
    森空岛干员阵容查询,
)
from .config import plugin_config
from .image import image_to_bytesio, text_to_image
from .manager import tokens
from .skland import (
    TOKEN_LENGTH,
    SKLand,
    SKLandError,
    api_v1_search_user_url,
    attendance_and_send_email,
    login_headers,
)
from .utils import get_qq_mail_address, is_base64

driver: Driver = get_driver()
default_command_start: str = tuple(driver.config.command_start)[0]  # noqa: RUF015

token_str = f"""
【如何绑定森空岛 token】
方法一：点击下面链接，按照提示操作
{plugin_config.skl_link}
方法二：点击上面链接查看如何获取森空岛 token，
然后添加 bot 为好友，私聊发送“{default_command_start}绑定森空岛token <token>”
# 为了您的账号安全，请不要在群聊中直接发送 token！
""".strip()

no_token_str = f"""未绑定森空岛 token，请先绑定森空岛 token。\n\n{token_str}"""

help_str: str = f"""
{token_str}

【可用命令】
- {default_command_start}绑定森空岛token <token>    # 绑定森空岛 token
- {default_command_start}解除绑定全部森空岛token    # 解除绑定全部森空岛 token

- {default_command_start}(关闭|开启)森空岛自动签到    # 关闭/开启森空岛自动签到
- {default_command_start}(关闭|开启)邮件提醒    # 关闭/开启邮件提醒

- {default_command_start}森空岛小秘书 [-n <name> | -i <skland_id>] [-u <uid>]    # 森空岛实时数据分析

- {default_command_start}森空岛干员阵容查询 [<uid>]    # 查询已有干员
- {default_command_start}干员列表 [-n <name> | -i <skland_id>] [-u <uid>]    # 查询自己或别人的干员列表
- {default_command_start}未拥有干员 [<uid>]    # 查询未拥有干员

- {default_command_start}我的仓库  # 查询仓库材料
- {default_command_start}已消耗材料 [<uid>]    # 查询养成总消耗
- {default_command_start}满练还差多少 [<uid>]    # 查询满练差多少材料

- {default_command_start}森空岛用户绑定角色 [-n <name> | -i <skland_id>]    # 查询森空岛用户绑定的角色

# <uid> 为一串数字，可在游戏主界面昵称下方找到。
# <uid> 为可选参数。若不指定 <uid>，则查询官网绑定的默认角色。
""".strip()

# - {default_command_start}解绑森空岛token <token>    # 解绑一个森空岛 token
# - {default_command_start}解绑所有森空岛token    # 解绑所有森空岛 token

DISABLE_REMINDER_MESSAGE = (
    "\n\n——\n如需关闭邮件提醒，请使用 QQ 向 bot 发送 “关闭邮件提醒”。"
)

__plugin_meta__ = PluginMetadata(
    name="森空岛小助手",
    description="明日方舟森空岛工具，提供自动签到、干员查询、仓库查询等各种实用功能。",
    usage=help_str,
)

skl_assistant_parser = ArgumentParser(
    prog="森空岛小秘书",
    description="森空岛实时数据分析",
    # formatter_class=argparse.RawTextHelpFormatter,
)
skl_assistant_group = skl_assistant_parser.add_mutually_exclusive_group()
skl_assistant_group.add_argument("-n", "--skland-name", help="森空岛昵称")
skl_assistant_group.add_argument("-i", "--skland-user-id", help="森空岛 ID")
skl_assistant_parser.add_argument("-u", "--game-uid", help="游戏角色 UID")
skl_assistant_parser.add_argument(
    "-v", "--verbose", action="store_true", help="输出更详细的信息"
)

skl_character_list_parser = ArgumentParser(
    prog="干员列表",
    description="森空岛干员列表查询工具",
    # formatter_class=argparse.RawTextHelpFormatter,
)
skl_character_list_group = skl_character_list_parser.add_mutually_exclusive_group()
skl_character_list_group.add_argument("-n", "--skland-name", help="森空岛昵称")
skl_character_list_group.add_argument("-i", "--skland-user-id", help="森空岛 ID")
skl_character_list_parser.add_argument("-u", "--game-uid", help="游戏角色 UID")
# parser.add_argument(
#     '-s', '--sort',
#     choices=['RARITY', 'LEVEL', 'PROFESSION', 'FAVOR', 'SKILLLEVEL', 'ONLINETIME', 'OBTAINTIME',
#              'R', 'L', 'P', 'F', 'S', 'O', 'G'],
#     help='排序方式:\n'
#          '  RARITY (R)     - 稀有度\n'
#          '  LEVEL (L)      - 等级\n'
#          '  PROFESSION (P) - 职业\n'
#          '  FAVOR (F)      - 好感度\n'
#          '  SKILLLEVEL (S) - 技能等级\n'
#          '  ONLINETIME (O) - 在线时间\n'
#          '  OBTAINTIME (G) - 获取时间'
# )
# parser.add_argument('-r', '--reversed', action='store_true', help='从大到小排序')
# parser.add_argument(
#     '--filter-owned',
#     choices=['TRUE', 'FALSE'],
#     help='过滤已拥有 (TRUE/FALSE)'
# )
# parser.add_argument(
#     '--filter-rarity',
#     help='过滤稀有度，格式为 [1-6] 或 [1-6]-[1-6]'
# )
# parser.add_argument('--filter-profession', help='过滤职业')

skl_binding_parser = ArgumentParser(
    prog="森空岛用户绑定角色",
    description="森空岛用户绑定角色查询工具",
    # formatter_class=argparse.RawTextHelpFormatter,
)
skl_binding_group = skl_binding_parser.add_mutually_exclusive_group()
skl_binding_group.add_argument("-n", "--skland-name", help="森空岛昵称")
skl_binding_group.add_argument("-i", "--skland-user-id", help="森空岛 ID")

matcher_group = MatcherGroup(priority=1, block=False)
bind_skl_token_command = matcher_group.on_command("绑定森空岛token")
bind_skl_token_regex = matcher_group.on_regex(
    r"""{"code":0,"data":{"content":"(.+)"},"msg":".+"}"""
)
unbind_skl_token = matcher_group.on_command(
    "删除森空岛token", aliases={"解绑森空岛token"}, permission=SUPERUSER
)
unbind_all_skl_token = matcher_group.on_command(
    "解除绑定全部森空岛token",
    aliases={
        "解除全部森空岛token绑定",
        "解除绑定所有森空岛token",
        "解除所有森空岛token绑定",
    },
)

skl_auto_attendance = matcher_group.on_keyword({"森空岛自动签到"})
skl_email_remind = matcher_group.on_keyword({"邮件提醒"})
skl_attendance_all = matcher_group.on_command("森空岛签到全部", permission=SUPERUSER)

skl_assistant = matcher_group.on_shell_command(
    "森空岛小秘书", aliases={"森空岛助手", "森空岛小助手"}, parser=skl_assistant_parser
)

skl_query = matcher_group.on_command("森空岛查询", aliases={"森空岛干员阵容查询"})
skl_character_list = matcher_group.on_shell_command(
    "干员列表",
    aliases={
        "已有干员练度",
        "已有干员",
        "干员练度",
        "我的干员",
        "我的干员练度",
        "已拥有干员练度",
        "已拥有干员",
    },
    parser=skl_character_list_parser,
)
skl_missing_characters = matcher_group.on_command("未拥有干员")

skl_my_depot = matcher_group.on_command("我的仓库", aliases={"已有材料", "仓库材料"})
skl_consumed_items = matcher_group.on_command("已消耗材料", aliases={"养成总消耗"})
skl_missing_items = matcher_group.on_command(
    "满练需要材料", aliases={"满练差多少材料", "满练还差多少"}
)

skl_binding = matcher_group.on_shell_command(
    "森空岛用户绑定角色",
    aliases={"森空岛角色绑定", "森空岛用户绑定列表"},
    parser=skl_binding_parser,
)


@scheduler.scheduled_job("cron", hour=0)
# @driver.on_startup
async def skl_sign_in_all() -> list[dict[str, Any] | BaseException]:
    logger.info("开始森空岛自动签到")
    enabled_tokens = await tokens.filter(enabled=True)
    tasks = [
        attendance_and_send_email(
            item.token, item.remind, item.email, DISABLE_REMINDER_MESSAGE
        )
        for item in enabled_tokens
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    for result in results:
        logger.info(repr(result))
    return results


@driver.on_startup
async def _():
    on_startup()


async def get_character(  # noqa: RET503
    *,
    matcher: Matcher,
    skland: SKLand,
    qq: int,
    uid: str | None,
    app_code: str = "arknights",
) -> dict[str, Any]:
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
    token_list = await tokens.filter(qq=qq)
    if not token_list:
        await matcher.finish(no_token_str)

    for item in token_list:
        # 尝试登录，如果登录失败则直接抛出异常
        await skland.login_by_token(item.token)
        player_binding = await skland.player_binding()
        character = skland.get_character(player_binding, uid, app_code)
        if character is not None:
            return character
    else:
        await matcher.finish("该账号未绑定该角色。")


@bind_skl_token_command.handle()
async def bind_skl_token_command_func(
    matcher: Matcher,
    bot: Bot,
    event: MessageEvent,
    message: Annotated[Message, CommandArg()],
) -> None:
    token = message.extract_plain_text().strip()
    return await bind_skl_token_func(matcher, bot, event, token)


@bind_skl_token_regex.handle()
async def bind_skl_token_regex_func(
    matcher: Matcher, bot: Bot, event: MessageEvent, group: tuple[str] = RegexGroup()
) -> None:
    token = group[0].strip()
    return await bind_skl_token_func(matcher, bot, event, token)


async def bind_skl_token_func(
    matcher: Matcher, bot: Bot, event: MessageEvent, token: str
) -> None:
    # 在群聊中发送消息时尝试撤回消息
    if isinstance(event, GroupMessageEvent):
        try:
            await bot.delete_msg(message_id=event.message_id)
        except Exception as e:
            logger.warning(f"尝试撤回群聊消息失败：{e}")

    try:
        if not token:
            await matcher.finish(help_str)

        if not (len(token) == TOKEN_LENGTH and is_base64(token)):
            await matcher.finish(
                "token 格式错误，请确认 token 不带引号。如需帮助，请发送“help sklassistant”。"
            )

        if await tokens.has_token(token):
            await matcher.finish("token 已存在。")

        await SKLand().login_by_token(token)

        await tokens.add_item(event.user_id, get_qq_mail_address(event.user_id), token)
        await matcher.send(
            "成功绑定森空岛 token。\n立即进行一次签到。以后将于每日 00:00 签到。\n已默认开启邮件提醒，签到结果将发送到你的 QQ 邮箱。如不需要邮件提醒，请发送 “关闭邮件提醒”。"
        )

        result: dict[str, Any] = await attendance_and_send_email(
            token, True, get_qq_mail_address(event.user_id), DISABLE_REMINDER_MESSAGE
        )
        await matcher.finish(result["msg"])

    except SKLandError as e:
        await matcher.send(f"绑定森空岛 token 失败：{e}")
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


@unbind_skl_token.handle()
async def unbind_skl_token_func(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    token: str = message.extract_plain_text().strip()
    if not token:
        await unbind_skl_token.finish(
            f"请在命令后面跟上要解绑的 token。如果要解绑所有 token，请发送“{default_command_start}解绑所有森空岛token”。"
        )

    if len(token) != TOKEN_LENGTH or not is_base64(token):
        await unbind_skl_token.finish(
            "token 格式错误，请确认 token 不带引号。如需帮助，请发送“绑定森空岛token”。"
        )

    if not await tokens.filter(qq=event.user_id, token=token):
        await unbind_skl_token.finish("未找到该 token。")

    await tokens.remove_item("token", token)

    await unbind_skl_token.finish("成功删除森空岛token。")


@unbind_all_skl_token.handle()
async def unbind_all_skl_token_func(matcher: Matcher, event: MessageEvent) -> None:
    if not await tokens.filter(qq=event.user_id):
        await unbind_all_skl_token.finish("还没有绑定过森空岛 token。")

    await tokens.remove_item("qq", event.user_id)

    await unbind_all_skl_token.finish("成功解除绑定全部森空岛token。")


@skl_auto_attendance.handle()
async def skl_auto_attendance_func(
    event: MessageEvent, message: str = EventPlainText()
) -> None:
    if "关闭" in message:
        enable: bool = False
    elif "开启" in message:
        enable = True
    else:
        await skl_auto_attendance.finish()

    token_list = await tokens.filter(qq=event.user_id)
    if not token_list:
        await skl_auto_attendance.finish(no_token_str)

    await tokens.set_enable_state("qq", event.user_id, enable)

    if enable:
        await skl_auto_attendance.send(
            "已开启森空岛自动签到。\n立即进行一次签到。以后将于每日 00:00 签到。"
        )
        tasks = (
            attendance_and_send_email(
                item.token, item.remind, item.email, DISABLE_REMINDER_MESSAGE
            )
            for item in token_list
        )
        results: list[dict[str, Any] | BaseException] = await asyncio.gather(
            *tasks, return_exceptions=True
        )
        await skl_auto_attendance.finish(
            "\n".join(
                result["msg"] if isinstance(result, dict) else repr(result)
                for result in results
            )
        )
    else:
        await skl_auto_attendance.finish("已关闭森空岛自动签到。")


@skl_email_remind.handle()
async def skl_email_remind_func(
    event: MessageEvent, message: str = EventPlainText()
) -> None:
    if "关闭" in message:
        remind: bool = False
    elif "开启" in message:
        remind = True
    else:
        await skl_email_remind.finish()

    if not await tokens.filter(qq=event.user_id):
        await skl_email_remind.finish(no_token_str)

    await tokens.set_remind_state("qq", event.user_id, remind)

    if remind:
        await skl_email_remind.finish(
            "已开启邮件提醒。以后签到结果将发送到您的 QQ 邮箱。"
        )
    else:
        await skl_email_remind.finish("已关闭邮件提醒。")


@skl_attendance_all.handle()
async def skl_attendance_all_func() -> None:
    results = await skl_sign_in_all()
    await skl_attendance_all.finish("\n".join(repr(result) for result in results))


@skl_assistant.handle()
async def skl_assistant_succeed_func(
    matcher: Matcher,
    event: MessageEvent,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    try:
        # 检查是否绑定了森空岛 token
        token_list = await tokens.filter(qq=event.user_id)
        if not token_list:
            await matcher.finish(no_token_str)
        token = token_list[0].token

        # 处理用户输入
        if args.skland_user_id is not None and not args.skland_user_id.isdigit():
            await matcher.finish(
                "森空岛 ID 必须为纯数字。如果您想使用森空岛昵称查询，请使用 -n/--skland-name 参数。\n"
                "发送“干员列表 -h”查看帮助。"
            )
        if args.game_uid is not None and not args.game_uid.isdigit():
            await matcher.finish(
                "游戏角色 UID 必须为纯数字。UID 可以在游戏主界面昵称下方找到。\n"
                "发送“干员列表 -h”查看帮助。"
            )

        skland = SKLand()
        if args.skland_name is not None:  # 使用森空岛搜索功能
            await skland.login_by_token(token)

            url = httpx.URL(api_v1_search_user_url).copy_merge_params(
                dict(keyword=args.skland_name, pageSize=20)  # noqa: C408
            )
            search_result_obj = await skland._request(
                "GET", str(url), login_headers, json=None, sign=True
            )
            search_user = SearchUser.model_validate(
                search_result_obj, strict=False, extra="allow"
            )
            if search_user.data.list:
                args.skland_user_id = search_user.data.list[0].user.id
            else:
                await matcher.finish(f"未找到用户 {args.skland_name}。")

        # 尝试登录
        if getattr(skland, "token", None) != token:
            await skland.login_by_token(token)

        # 获取用户绑定的角色列表 player_binding
        player_binding_obj = await skland.player_binding(uid=args.skland_user_id)
        binding_character = skland.get_character(
            player_binding_obj, args.game_uid, app_code="arknights"
        )

        if binding_character is None:
            await matcher.finish("未找到该用户的绑定角色。")

        # 获取当前游戏状态 player_info
        obj = await skland.get_player_info(
            uid=binding_character["uid"], user_id=args.skland_user_id
        )
        player_info = PlayerInfo.model_validate(obj, strict=False, extra="allow")

        result = await skl_assistant_func(player_info, args.verbose)

        if len(result) > 512:
            image = text_to_image(
                result,
                tabs=list(accumulate([])),
                font_size=14,
                row_spacing=0,
            )
            await matcher.send(
                MessageSegment.image(image_to_bytesio(image.convert("L"), format="PNG"))
            )
        else:
            await matcher.send(result)

    except SKLandError as e:
        await matcher.send(str(e))
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


@skl_assistant.handle()
async def skl_assistant_fail_func(
    args: Annotated[ParserExit, ShellCommandArgs()],
) -> None:
    await skl_assistant.finish(skl_assistant_parser.format_help())


@skl_query.handle()
async def skl_query_func(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    uid: str | None = message.extract_plain_text().strip()
    if not uid.isdigit():
        uid = None

    token_list = await tokens.filter(qq=event.user_id)
    if not token_list:
        await matcher.finish(no_token_str)

    exception = None
    for item in token_list:
        token = item.token
        try:
            if type(matcher) is skl_assistant:
                result: str = await 森空岛实时数据分析(token, uid)
            else:
                result = await 森空岛干员阵容查询(token, uid)
        except Exception as e:
            exception = e
        else:
            if len(result) > 512:
                await matcher.send(
                    MessageSegment.image(image_to_bytesio(text_to_image(result)))
                )
            else:
                await matcher.send(result)

    if isinstance(exception, SKLandError):
        await matcher.send(str(exception))
        raise exception
    elif isinstance(exception, Exception):
        await matcher.send(repr(exception))
        raise exception


@skl_missing_characters.handle()
@skl_my_depot.handle()
@skl_consumed_items.handle()
@skl_missing_items.handle()
async def _(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    try:
        if isinstance(matcher, skl_missing_characters):
            await skl_missing_characters_func(matcher, event, message)
        elif isinstance(matcher, skl_my_depot):
            await skl_my_depot_func(matcher, event, message)
        elif isinstance(matcher, skl_consumed_items):
            await skl_consumed_or_missing_items_func(matcher, event, message)
        elif isinstance(matcher, skl_missing_items):
            await skl_consumed_or_missing_items_func(matcher, event, message)
        else:
            await matcher.finish("更多功能正在锐意开发中，一键三连可以催更哦~")

    except SKLandError as e:
        await matcher.send(str(e))
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


@skl_character_list.handle()
async def skl_character_list_succeed_func(
    matcher: Matcher,
    event: MessageEvent,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    try:
        # 检查是否绑定了森空岛 token
        token_list = await tokens.filter(qq=event.user_id)
        if not token_list:
            await matcher.finish(no_token_str)
        token = token_list[0].token

        if args.skland_user_id is not None and not args.skland_user_id.isdigit():
            await matcher.finish(
                "森空岛 ID 必须为纯数字。如果您想使用森空岛昵称查询，请使用 -n/--skland-name 参数。\n发送“干员列表 -h”查看帮助。"
            )
        if args.game_uid is not None and not args.game_uid.isdigit():
            await matcher.finish(
                "游戏角色 UID 必须为纯数字。UID 可以在游戏主界面昵称下方找到。\n发送“干员列表 -h”查看帮助。"
            )

        skland = SKLand()
        if args.skland_name is not None:  # 使用森空岛搜索功能
            await skland.login_by_token(token)

            url = httpx.URL(api_v1_search_user_url).copy_merge_params(
                dict(keyword=args.skland_name, pageSize=20)  # noqa: C408
            )
            search_result_obj = await skland._request(
                "GET", str(url), login_headers, json=None, sign=True
            )
            search_user = SearchUser.model_validate(
                search_result_obj, strict=False, extra="allow"
            )
            if search_user.data.list:
                args.skland_user_id = search_user.data.list[0].user.id
            else:
                await matcher.finish(f"未找到用户 {args.skland_name}。")

        # 尝试登录
        if getattr(skland, "token", None) != token:
            await skland.login_by_token(token)

        player_binding_obj = await skland.player_binding(uid=args.skland_user_id)
        binding_character = skland.get_character(
            player_binding_obj, args.game_uid, app_code="arknights"
        )

        if binding_character is None:
            await matcher.finish("未找到该用户的绑定角色。")

        obj = await skland.get_player_info(
            uid=binding_character["uid"], user_id=args.skland_user_id
        )

        player_info = PlayerInfo.model_validate(obj, strict=False, extra="allow")

        owned_character_id_set = {
            character.char_id for character in player_info.data.chars
        }
        not_owned_character_id_set = (
            game_data.characters.keys() - owned_character_id_set
        )

        lines: list[str] = []

        lines.append(
            f"{binding_character['channelName']}账号 {binding_character['nickName']}（{binding_character['uid']}）"
        )
        lines.append("________________")
        lines.append("")
        lines.append("/- 干员练度详情 -/")
        lines.append("")
        lines.append(
            "干员 ID\t干员代号\t精英化\0\t等级\0\t技能\0\t专精\t模组\t信赖\0\t获取时间\tEXP\0\t龙门币\0\t钱书比\0\t物品价值\0"
        )

        item_info_list = ItemInfoList()

        for skl_character in player_info.data.chars:
            character = game_data.characters.by_id(skl_character.char_id)

            # 计算养成到当前练度所需材料
            char_item_info_list = character.养成消耗(
                目标精英化阶段=skl_character.evolve_phase,
                目标等级=skl_character.level,
                目标技能等级=skl_character.main_skill_lvl,
                目标技能专精等级列表=[
                    skl_skill.specialize_level for skl_skill in skl_character.skills
                ],
                目标模组等级字典={
                    skl_equip.id: 0 if skl_equip.locked else skl_equip.level
                    for skl_equip in skl_character.equip
                },
            ).combine()
            counter = char_item_info_list.counter()
            char_yituliu_value = char_item_info_list.yituliu_item_value(strict=False)
            item_info_list.extend(char_item_info_list)

            skill_spec_text = f"专{''.join(str(skl_skill.specialize_level) for skl_skill in skl_character.skills)}"
            equip_text_list = []
            for skl_equip in skl_character.equip:
                equip = character.get_uniequip(skl_equip.id)
                if equip.is_original:
                    continue  # 跳过初始模组
                equip_level = 0 if skl_equip.locked else skl_equip.level
                equip_text_list.append(f"{equip.type_name2}{equip_level}")

            lines.append(
                f"{character.id}\t"
                f"{character.name}\t"
                f"精{skl_character.evolve_phase}\0\t"
                f"{skl_character.level}级\0\t"
                f"{skl_character.main_skill_lvl}级\0\t"
                f"{skill_spec_text}\t"
                f"{' '.join(equip_text_list)}\t"
                f"{skl_character.favor_percent}%\0\t"
                f"{datetime.fromtimestamp(skl_character.gain_time, CST).strftime('%Y-%m-%d %H:%M:%S')}\t"
                f"{counter.get('exp', 0)}\0\t"
                f"{counter.get('4001', 0)}\0\t"
                f"{divide(counter.get('4001', 0), counter.get('exp', 0)):.4f}\0\t"
                f"{char_yituliu_value:.2f}\0"
            )
            """char_377_gdglow\t澄闪\t精2\0\t60级\0\t7级\0\t专333\tX3 Y0\t100%\0\t2022-09-01 12:34:56\t114514\0\t1919810\0\t1.4142\0\t1145.14\0"""

        for character_id in not_owned_character_id_set:
            character = game_data.characters.by_id(character_id)
            lines.append(f"{character.id}\t{character.name}\t未拥有")

        counter = item_info_list.counter()
        yituliu_item_value = item_info_list.yituliu_item_value(strict=False)
        lines.append("")
        lines.append(
            f"养成到当前练度共消耗 EXP×{counter.get('exp', 0)}、龙门币×{counter.get('4001', 0)}，钱书比 {divide(counter.get('4001', 0), counter.get('exp', 0)):.4f}"
        )
        lines.append(f"养成到当前练度共消耗的材料相当于 {yituliu_item_value:.2f} 理智")
        lines.append("")
        lines.append("________________")
        lines.append("# 物品价值数据来自 明日方舟一图流 - 物品价值表")
        lines.append("https://ark.yituliu.cn/material/value")
        lines.append("")
        lines.append("# Generated by BioBot")
        lines.append("# Made by bilibili@Bio-Hazard")
        lines.append("https://space.bilibili.com/37179776")

        result = "\n".join(lines)

        if len(result) > 512:
            image = text_to_image(
                result,
                tabs=list(accumulate([10, 9, 2.5, 2, 0.5, 3, 8, 0.5, 14, 4.5, 4, 5])),
                font_size=10,
                row_spacing=0,
            )
            await matcher.send(
                MessageSegment.image(image_to_bytesio(image.convert("L"), format="PNG"))
            )
        else:
            await matcher.send(result)

    except SKLandError as e:
        await matcher.send(str(e))
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


@skl_character_list.handle()
async def skl_character_list_fail_func(
    args: Annotated[ParserExit, ShellCommandArgs()],
) -> None:
    await skl_character_list.finish(skl_character_list_parser.format_help())


async def skl_missing_characters_func(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    skland = SKLand()
    binding_character = await get_character(
        matcher=matcher,
        skland=skland,
        qq=event.user_id,
        uid=message.extract_plain_text().strip(),
        app_code="arknights",
    )

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj, strict=False, extra="allow")

    missing_character_list = []
    for character_id, character in game_data.characters.items():
        for skl_character in cultivate_player.data.characters:
            if skl_character.id == character_id:
                break
        else:
            missing_character_list.append(character)

    lines: list[str] = []

    lines.append(
        f"{binding_character['channelName']}账号 {binding_character['nickName']}（{binding_character['uid']}）"
    )
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


async def skl_my_depot_func(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    skland = SKLand()
    binding_character = await get_character(
        matcher=matcher,
        skland=skland,
        qq=event.user_id,
        uid=message.extract_plain_text().strip(),
        app_code="arknights",
    )

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj, strict=False, extra="allow")

    item_info_list: ItemInfoList = ItemInfoList()
    for item in cultivate_player.data.items:
        item_info_list.append(ItemInfo(item_id=item.id, count=item.count))
    item_info_list.sort_in_place_by_sort_id()

    yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

    lines: list[str] = []

    lines.append(
        f"{binding_character['channelName']}账号 {binding_character['nickName']}（{binding_character['uid']}）"
    )
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
        item_info_list.extend(
            character.养成消耗(
                目标精英化阶段=skl_character.evolve_phase,
                目标等级=skl_character.level,
                目标技能等级=skl_character.main_skill_level,
                目标技能专精等级列表=[skill.level for skill in skl_character.skills],
                目标模组等级字典={
                    equip.id: equip.level for equip in skl_character.equips
                },
            )
        )
    item_info_list.combine_in_place()
    item_info_list.sort_in_place_by_sort_id()
    return item_info_list


def get_missing_item_info_list(cultivate_player: CultivatePlayer) -> ItemInfoList:
    item_info_list: ItemInfoList = ItemInfoList()
    owned_character_id_set = {
        character.id for character in cultivate_player.data.characters
    }
    not_owned_character_id_set = game_data.characters.keys() - owned_character_id_set
    for skl_character in cultivate_player.data.characters:
        character = game_data.characters.by_id(skl_character.id)
        item_info_list.extend(
            character.养成消耗(
                初始精英化阶段=skl_character.evolve_phase,
                初始等级=skl_character.level,
                初始技能等级=skl_character.main_skill_level,
                初始技能专精等级列表=[skill.level for skill in skl_character.skills],
                初始模组等级字典={
                    equip.id: equip.level for equip in skl_character.equips
                },
            )
        )
    for character_id in not_owned_character_id_set:
        character = game_data.characters.by_id(character_id)
        item_info_list.extend(character.养成消耗())
    item_info_list.combine_in_place()
    item_info_list.sort_in_place_by_sort_id()
    return item_info_list


async def skl_consumed_or_missing_items_func(
    matcher: Matcher, event: MessageEvent, message: Annotated[Message, CommandArg()]
) -> None:
    skland = SKLand()
    binding_character = await get_character(
        matcher=matcher,
        skland=skland,
        qq=event.user_id,
        uid=message.extract_plain_text().strip(),
        app_code="arknights",
    )

    obj = await skland.cultivate_player(binding_character["uid"])

    cultivate_player = CultivatePlayer.model_validate(obj, strict=False, extra="allow")

    if isinstance(matcher, skl_consumed_items):
        item_info_list = get_consumed_item_info_list(cultivate_player)
        title = "养成总消耗"
    else:
        item_info_list = get_missing_item_info_list(cultivate_player)
        title = "距离满练还差"

    yituliu_item_value = item_info_list.yituliu_item_value(strict=False)

    lines: list[str] = []

    lines.append(
        f"{binding_character['channelName']}账号 {binding_character['nickName']}（{binding_character['uid']}）"
    )
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


@skl_binding.handle()
async def skl_binding_succeed_func(
    matcher: Matcher,
    event: MessageEvent,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    try:
        # 检查是否绑定了森空岛 token
        token_list = await tokens.filter(qq=event.user_id)
        if not token_list:
            await matcher.finish(no_token_str)
        token = token_list[0].token

        if args.skland_user_id is not None and not args.skland_user_id.isdigit():
            await matcher.finish(
                "森空岛 ID 必须为纯数字。如果您想使用森空岛昵称查询，请使用 -n/--skland-name 参数。\n发送“森空岛用户绑定角色 -h”查看帮助。"
            )

        skland = SKLand()
        if args.skland_name is not None:  # 使用森空岛搜索功能
            await skland.login_by_token(token)

            url = httpx.URL(api_v1_search_user_url).copy_merge_params(
                dict(keyword=args.skland_name, pageSize=20)  # noqa: C408
            )
            search_result_obj = await skland._request(
                "GET", str(url), login_headers, json=None, sign=True
            )
            search_user = SearchUser.model_validate(
                search_result_obj, strict=False, extra="allow"
            )
            if search_user.data.list:
                args.skland_user_id = search_user.data.list[0].user.id
            else:
                await matcher.finish(f"未找到用户 {args.skland_name}。")

        # 如果查自己的（user_id is None），则尝试所有 token，否则只使用第一个 token
        if args.skland_user_id is not None:
            token_list = token_list[:1]

        for item in token_list:
            token = item.token

            # 尝试登录
            if getattr(skland, "token", None) != token:
                await skland.login_by_token(token)

            player_binding_obj = await skland.player_binding(uid=args.skland_user_id)
            player_binding = PlayerBinding.model_validate(
                player_binding_obj, strict=False, extra="allow"
            )

            lines: list[str] = []
            lines.append("用户绑定列表")
            lines.append("________________")
            for app_info in player_binding.data.list:
                lines.append("")
                lines.append(f"/- {app_info.app_code}（{app_info.app_name}） -/")
                lines.append("")
                for binding_character in app_info.binding_list:
                    lines.append(
                        f"{binding_character.channel_name}账号 {binding_character.nick_name}（{binding_character.uid}{'，默认' if binding_character.is_default else ''}）"
                    )
            lines.append("")
            lines.append("________________")
            lines.append("# Generated by BioBot")
            lines.append("# Made by bilibili@Bio-Hazard")
            lines.append("https://space.bilibili.com/37179776")

            await matcher.send("\n".join(lines))

    except SKLandError as e:
        await matcher.send(str(e))
        raise e
    except MatcherException as e:
        raise e
    except Exception as e:
        await matcher.send("发生了苏茜解决不了的错误呢，怎么回事呢？")
        raise e


@skl_binding.handle()
async def skl_binding_fail_func(
    args: Annotated[ParserExit, ShellCommandArgs()],
) -> None:
    await skl_binding.finish(skl_binding_parser.format_help())
