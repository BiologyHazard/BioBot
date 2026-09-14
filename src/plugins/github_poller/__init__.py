# ruff: noqa: E402

"""通过 GitHub REST API 轮询仓库变化并推送到 QQ。"""

from __future__ import annotations

from nonebot import require

require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")

from argparse import ArgumentTypeError
from typing import TYPE_CHECKING, Annotated

from nonebot import logger, on_shell_command
from nonebot.exception import FinishedException
from nonebot.params import ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.rule import ArgumentParser
from nonebot_plugin_apscheduler import scheduler

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

if TYPE_CHECKING:
    from nonebot.adapters.onebot.v11 import MessageEvent
    from nonebot_plugin_orm import AsyncSession

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


# 由 NoneBot 的 shell parser 负责引号、重复选项和参数边界。
ghp_parser = ArgumentParser(prog="ghp", description="GitHub 仓库轮询通知")
ghp_parser.add_argument("positional", nargs="*", help="子命令及其参数")
ghp_parser.add_argument(
    "--group",
    dest="groups",
    action="append",
    default=[],
    type=_target_id,
    help="群号（可重复）",
)
ghp_parser.add_argument(
    "--private",
    dest="privates",
    action="append",
    default=[],
    type=_target_id,
    help="QQ 号（可重复）",
)
ghp_parser.add_argument(
    "--branch", dest="branches", action="append", default=[], help="分支模式（可重复）"
)

ghp = on_shell_command(
    "ghp", parser=ghp_parser, permission=SUPERUSER, block=False, priority=5
)


@ghp.handle()
async def handle_ghp(
    event: MessageEvent,
    session: AsyncSession,
    args: Annotated[object, ShellCommandArgs()],
) -> None:
    # 所有子命令统一从这里分发，确保权限和错误提示行为一致。
    try:
        # 业务函数仍使用原先的简单参数结构，避免把 argparse Namespace 传入数据层。
        positional = list(getattr(args, "positional", []))
        groups = list(getattr(args, "groups", []))
        privates = list(getattr(args, "privates", []))
        branches = list(getattr(args, "branches", []))
        if not positional:
            await ghp.finish(HELP)
        command, *tokens = positional
        command = command.lower()

        if command == "help":
            result = HELP
        elif command == "subscribe":
            result = await subscribe(session, event, tokens, groups, privates, branches)
        elif command == "unsubscribe":
            result = await unsubscribe(session, event, tokens, groups, privates)
        elif command == "list":
            result = await list_subscriptions(session, event, groups, privates)
        elif command == "show":
            result = await show(session, event, tokens, groups, privates)
        elif command == "event":
            if not tokens:
                raise ValueError("用法：/ghp event list|add|remove|set ...")
            operation, *arguments = tokens
            if operation == "list":
                result = await event_list(arguments)
            elif operation in {"add", "remove", "set"}:
                result = await edit_events(
                    session, event, operation, arguments, groups, privates
                )
            else:
                raise ValueError(f"未知 event 操作：{operation}")
        elif command == "branch":
            if not tokens:
                raise ValueError("用法：/ghp branch add|remove|reset ...")
            operation, *arguments = tokens
            if operation not in {"add", "remove", "reset"}:
                raise ValueError(f"未知 branch 操作：{operation}")
            result = await edit_branches(
                session, event, operation, arguments, groups, privates
            )
        elif command in {"pause", "resume"}:
            result = await set_enabled(
                session, event, command == "resume", tokens, groups, privates
            )
        elif command == "poll":
            repository_id = None
            if tokens:
                repository_id = (await find_repository(session, tokens[0])).id
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
async def scheduled_poll() -> None:
    # APScheduler 负责周期触发，PollingService 还会用锁防止手动轮询重叠。
    await service.poll_all()


if not plugin_config.github_poller_github_token:
    logger.warning(
        "github_poller 未配置 GitHub Token：插件仍会运行，但只能读取公开仓库，"
        "且未认证 API 通常限制为每小时 60 次请求"
    )
