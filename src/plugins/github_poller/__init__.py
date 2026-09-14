# ruff: noqa: E402

"""通过 GitHub REST API 轮询仓库变化并推送到 QQ。"""

import sys

from nonebot import get_driver, require

require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")

from argparse import ArgumentTypeError
from typing import Annotated, Any

from nonebot import logger, on_shell_command
from nonebot.adapters.onebot.v11 import MessageEvent
from nonebot.exception import FinishedException, ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import ArgumentParser, Namespace
from nonebot_plugin_apscheduler import scheduler
from nonebot_plugin_orm import AsyncSession

from .commands import (
    HELP,
    edit_branches,
    edit_events,
    event_list,
    find_repository,
    list_subscriptions,
    set_enabled,
    show,
    status,
    subscribe,
    unsubscribe,
)
from .config import Config, plugin_config
from .service import service

__plugin_meta__ = PluginMetadata(
    name="GitHub 轮询通知",
    description="通过 GitHub REST API 轮询仓库动态并推送到 QQ",
    usage=HELP,
    type="application",
    config=Config,
)


def _target_id(value: str) -> str:
    """验证群号或 QQ 号，同时保留字符串避免大整数精度/格式问题。"""
    if not value.isdigit():
        raise ArgumentTypeError("目标 ID 必须是数字")
    return value


def _targets(parser: ArgumentParser, *, branches: bool = False) -> None:
    """向子命令添加统一的目标选项；subscribe 额外支持分支模式。"""
    parser.add_argument(
        "--group",
        dest="groups",
        action="append",
        default=[],
        type=_target_id,
        metavar="GROUP_ID",
        help="将订阅应用到指定群聊；可重复指定，缺省时使用当前群聊",
    )
    parser.add_argument(
        "--private",
        dest="privates",
        action="append",
        default=[],
        type=_target_id,
        metavar="QQ_ID",
        help="将订阅应用到指定私聊账号；可重复指定，私聊中必须显式提供目标",
    )
    if branches:
        parser.add_argument(
            "--branch",
            dest="branches",
            action="append",
            default=[],
            type=str,
            metavar="PATTERN",
            help="限制通知来源分支；支持分支名或通配模式，可重复指定（默认使用默认分支）",
        )


class NoColorArgumentParser(ArgumentParser):
    """为根解析器及所有子解析器统一关闭帮助信息颜色。"""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if sys.version_info >= (3, 14):
            kwargs.setdefault("color", False)
        super().__init__(*args, **kwargs)


ghp_parser = NoColorArgumentParser(
    prog="ghp",
    description="管理 GitHub 仓库订阅，并将仓库动态推送到 QQ。",
    epilog="仓库可写成 owner/repo 或 GitHub 仓库 URL；目标选项可重复指定。",
)
subparsers = ghp_parser.add_subparsers(
    title="命令", dest="command", required=True, metavar="COMMAND"
)

subscribe_parser = subparsers.add_parser(
    "subscribe",
    help="订阅或更新仓库通知",
    description="订阅仓库并设置事件、分支过滤器；重复执行会更新已有配置。",
)
subscribe_parser.add_argument(
    "repository",
    type=str,
    metavar="REPOSITORY",
    help="GitHub 仓库，格式为 owner/repo 或仓库 URL",
)
subscribe_parser.add_argument(
    "events",
    type=str,
    nargs="*",
    metavar="EVENT",
    help="事件过滤器，如 pr、pr.merged 或 default；不指定时使用默认事件集",
)
_targets(subscribe_parser, branches=True)

unsubscribe_parser = subparsers.add_parser(
    "unsubscribe",
    help="取消仓库通知",
    description="取消指定目标对仓库的订阅；当所有目标都取消后，仓库数据也会被清理。",
)
unsubscribe_parser.add_argument(
    "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
)
_targets(unsubscribe_parser)

list_parser = subparsers.add_parser(
    "list",
    help="列出目标的订阅",
    description="列出目标当前的所有 GitHub 仓库订阅及启用状态。",
)
_targets(list_parser)

show_parser = subparsers.add_parser(
    "show",
    help="查看仓库订阅配置",
    description="查看指定仓库的事件过滤器、分支过滤器和目标订阅状态。",
)
show_parser.add_argument(
    "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
)
_targets(show_parser)

event_parser = subparsers.add_parser(
    "event",
    help="管理事件过滤器",
    description="查看或修改仓库订阅的 GitHub 事件过滤器。",
)
event_commands = event_parser.add_subparsers(
    title="事件操作", dest="operation", required=True, metavar="OPERATION"
)
event_list_parser = event_commands.add_parser(
    "list",
    help="列出支持的事件",
    description="列出所有事件类别；指定类别可查看该类别下的原子事件。",
)
event_list_parser.add_argument(
    "category",
    type=str,
    nargs="?",
    metavar="CATEGORY",
    help="可选的事件类别，如 pr；省略时列出所有类别",
)
for operation in ("add", "remove", "set"):
    operation_parser = event_commands.add_parser(
        operation,
        help={
            "add": "添加事件过滤器",
            "remove": "移除事件过滤器",
            "set": "覆盖事件过滤器",
        }[operation],
        description={
            "add": "为目标订阅追加事件过滤器。",
            "remove": "从目标订阅中移除事件过滤器。",
            "set": "用给定事件过滤器覆盖目标订阅的现有配置。",
        }[operation],
    )
    operation_parser.add_argument(
        "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
    )
    operation_parser.add_argument(
        "events",
        type=str,
        nargs="+",
        metavar="EVENT",
        help="一个或多个事件过滤器，如 pr、pr.merged 或 all",
    )
    _targets(operation_parser)

branch_parser = subparsers.add_parser(
    "branch",
    help="管理分支过滤器",
    description="查看范围由订阅事件通知的分支；模式支持通配符。",
)
branch_commands = branch_parser.add_subparsers(
    title="分支操作", dest="operation", required=True, metavar="OPERATION"
)
for operation in ("add", "remove"):
    operation_parser = branch_commands.add_parser(
        operation,
        help={"add": "添加分支过滤器", "remove": "移除分支过滤器"}[operation],
        description={
            "add": "为目标订阅追加分支模式。",
            "remove": "从目标订阅中移除分支模式。",
        }[operation],
    )
    operation_parser.add_argument(
        "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
    )
    operation_parser.add_argument(
        "patterns",
        type=str,
        nargs="+",
        metavar="PATTERN",
        help="一个或多个分支名或通配模式，如 main、release/*",
    )
    _targets(operation_parser)
reset_parser = branch_commands.add_parser(
    "reset",
    help="重置分支过滤器",
    description="将目标订阅的分支过滤器恢复为仓库默认分支。",
)
reset_parser.add_argument(
    "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
)
_targets(reset_parser)

for operation in ("pause", "resume"):
    operation_parser = subparsers.add_parser(
        operation,
        help={"pause": "暂停仓库轮询", "resume": "恢复仓库轮询"}[operation],
        description={
            "pause": "暂停目标订阅的通知推送，但保留订阅配置。",
            "resume": "恢复目标订阅的通知推送。",
        }[operation],
    )
    operation_parser.add_argument(
        "repository", type=str, metavar="REPOSITORY", help="已订阅的 GitHub 仓库"
    )
    _targets(operation_parser)

poll_parser = subparsers.add_parser(
    "poll",
    help="立即轮询仓库",
    description="立即执行一次轮询；省略仓库时轮询所有已订阅仓库。",
)
poll_parser.add_argument(
    "repository",
    type=str,
    nargs="?",
    metavar="REPOSITORY",
    help="可选的已订阅仓库；省略时轮询全部仓库",
)
subparsers.add_parser(
    "status",
    help="查看轮询状态",
    description="查看 GitHub API、订阅数量、最近轮询和失败状态。",
)
subparsers.add_parser(
    "help", help="显示命令帮助", description="显示 ghp 命令的完整帮助信息。"
)

ghp = on_shell_command(
    "ghp", parser=ghp_parser, permission=SUPERUSER, block=False, priority=5
)


@ghp.handle()
async def handle_parser_exit(
    parser_exit: Annotated[ParserExit, ShellCommandArgs()],
) -> None:
    """返回 argparse 生成的帮助或错误信息。"""
    await ghp.finish(parser_exit.message)


@ghp.handle()
async def handle_ghp(
    event: MessageEvent,
    session: AsyncSession,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    # 所有子命令统一从这里分发，确保权限和错误提示行为一致。
    try:
        command = args.command

        if command == "help":
            result = HELP
        elif command == "subscribe":
            result = await subscribe(
                session,
                event,
                [args.repository, *args.events],
                args.groups,
                args.privates,
                args.branches,
            )
        elif command == "unsubscribe":
            result = await unsubscribe(
                session, event, [args.repository], args.groups, args.privates
            )
        elif command == "list":
            result = await list_subscriptions(
                session, event, args.groups, args.privates
            )
        elif command == "show":
            result = await show(
                session, event, [args.repository], args.groups, args.privates
            )
        elif command == "event":
            operation = args.operation
            if operation == "list":
                result = await event_list(
                    [args.category] if args.category is not None else []
                )
            else:
                result = await edit_events(
                    session,
                    event,
                    operation,
                    [args.repository, *args.events],
                    args.groups,
                    args.privates,
                )
        elif command == "branch":
            operation = args.operation
            arguments = [args.repository]
            if operation in {"add", "remove"}:
                arguments.extend(args.patterns)
            result = await edit_branches(
                session, event, operation, arguments, args.groups, args.privates
            )
        elif command in {"pause", "resume"}:
            result = await set_enabled(
                session,
                event,
                command == "resume",
                [args.repository],
                args.groups,
                args.privates,
            )
        elif command == "poll":
            repository_id = None
            if args.repository:
                repository_id = (await find_repository(session, args.repository)).id
                await session.rollback()
            await service.poll_all(repository_id)
            result = "轮询完成"
        elif command == "status":
            result = await status()
        else:
            raise ValueError(f"未知子命令：{command}，使用 /ghp help 查看帮助")
        await ghp.finish(result)
    except ValueError as exc:
        await ghp.finish(f"参数错误：{exc}")
    except FinishedException:
        raise
    except Exception as exc:
        error = service._safe_error(exc)
        logger.exception("执行 ghp 命令失败")
        await ghp.finish(f"操作失败：{error}")


@scheduler.scheduled_job(
    "interval",
    seconds=plugin_config.github_poller_poll_interval,
    id="github_poller",
    max_instances=1,
    coalesce=True,
)
@get_driver().on_startup
async def scheduled_poll() -> None:
    # APScheduler 负责周期触发，PollingService 还会用锁防止手动轮询重叠。
    await service.poll_all()


if not plugin_config.github_poller_github_token:
    logger.warning(
        "github_poller 未配置 GitHub Token：插件仍会运行，但只能读取公开仓库，"
        "且未认证 API 通常限制为每小时 60 次请求"
    )
