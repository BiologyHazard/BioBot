# ruff: noqa: E402

"""通过 GitHub REST API 轮询仓库变化并推送到 QQ。"""

import sys

from nonebot import get_driver, require

require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")

from argparse import ArgumentTypeError
from typing import Annotated

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
        "--group", dest="groups", action="append", default=[], type=_target_id
    )
    parser.add_argument(
        "--private", dest="privates", action="append", default=[], type=_target_id
    )
    if branches:
        parser.add_argument("--branch", dest="branches", action="append", default=[])


class NoColorArgumentParser(ArgumentParser):
    """为根解析器及所有子解析器统一关闭帮助信息颜色。"""

    def __init__(self, *args, **kwargs) -> None:
        if sys.version_info >= (3, 14):
            kwargs.setdefault("color", False)
        super().__init__(*args, **kwargs)


ghp_parser = NoColorArgumentParser(prog="ghp", description="GitHub 仓库订阅通知")
subparsers = ghp_parser.add_subparsers(title="commands", dest="command", required=True)

subscribe_parser = subparsers.add_parser(
    "subscribe", help="订阅或更新仓库通知", description="订阅或更新仓库通知"
)
subscribe_parser.add_argument("repository")
subscribe_parser.add_argument("events", nargs="*")
_targets(subscribe_parser, branches=True)

unsubscribe_parser = subparsers.add_parser(
    "unsubscribe", help="取消仓库通知", description="取消仓库通知"
)
unsubscribe_parser.add_argument("repository")
_targets(unsubscribe_parser)

list_parser = subparsers.add_parser(
    "list", help="列出目标的订阅", description="列出目标的订阅"
)
_targets(list_parser)

show_parser = subparsers.add_parser(
    "show", help="查看仓库订阅配置", description="查看仓库订阅配置"
)
show_parser.add_argument("repository")
_targets(show_parser)

event_parser = subparsers.add_parser(
    "event", help="管理事件过滤器", description="管理事件过滤器"
)
event_commands = event_parser.add_subparsers(dest="operation", required=True)
event_list_parser = event_commands.add_parser(
    "list", help="列出支持的事件", description="列出支持的事件"
)
event_list_parser.add_argument("category", nargs="?")
for operation in ("add", "remove", "set"):
    operation_parser = event_commands.add_parser(
        operation, help=f"{operation} 事件过滤器", description=f"{operation} 事件过滤器"
    )
    operation_parser.add_argument("repository")
    operation_parser.add_argument("events", nargs="+")
    _targets(operation_parser)

branch_parser = subparsers.add_parser(
    "branch", help="管理分支过滤器", description="管理分支过滤器"
)
branch_commands = branch_parser.add_subparsers(dest="operation", required=True)
for operation in ("add", "remove"):
    operation_parser = branch_commands.add_parser(
        operation, help=f"{operation} 分支过滤器", description=f"{operation} 分支过滤器"
    )
    operation_parser.add_argument("repository")
    operation_parser.add_argument("patterns", nargs="+")
    _targets(operation_parser)
reset_parser = branch_commands.add_parser(
    "reset", help="重置分支过滤器", description="重置分支过滤器"
)
reset_parser.add_argument("repository")
_targets(reset_parser)

for operation in ("pause", "resume"):
    operation_parser = subparsers.add_parser(
        operation, help=f"{operation} 仓库轮询", description=f"{operation} 仓库轮询"
    )
    operation_parser.add_argument("repository")
    _targets(operation_parser)

poll_parser = subparsers.add_parser(
    "poll", help="立即轮询仓库", description="立即轮询仓库"
)
poll_parser.add_argument("repository", nargs="?")
subparsers.add_parser("status", help="查看轮询状态", description="查看轮询状态")
subparsers.add_parser("help", help="显示命令帮助", description="显示命令帮助")

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
