"""通过 GitHub REST API 轮询仓库变化并推送到 QQ。"""

from __future__ import annotations

from typing import Annotated

from nonebot import logger, on_command, require
from nonebot.adapters.onebot.v11 import Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata
from nonebot.exception import FinishedException

from .config import Config, plugin_config

require("nonebot_plugin_orm")
require("nonebot_plugin_apscheduler")

from nonebot_plugin_apscheduler import scheduler  # noqa: E402
from nonebot_plugin_orm import AsyncSession  # noqa: E402

from .commands import (  # noqa: E402
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
from .events import parse_args  # noqa: E402
from .service import service  # noqa: E402


__plugin_meta__ = PluginMetadata(
    name="GitHub 轮询通知",
    description="通过 GitHub REST API 轮询仓库动态并推送到 QQ",
    usage=HELP,
    type="application",
    config=Config,
)

ghp = on_command("ghp", permission=SUPERUSER, block=True, priority=5)


@ghp.handle()
async def handle_ghp(
    event: MessageEvent,
    session: AsyncSession,
    message: Annotated[Message, CommandArg()],
) -> None:
    try:
        parsed = parse_args(message.extract_plain_text().strip())
        if not parsed.positional:
            await ghp.finish(HELP)
        command, *tokens = parsed.positional
        command = command.lower()

        if command == "help":
            result = HELP
        elif command == "subscribe":
            result = await subscribe(
                session, event, tokens, parsed.groups, parsed.privates, parsed.branches
            )
        elif command == "unsubscribe":
            result = await unsubscribe(
                session, event, tokens, parsed.groups, parsed.privates
            )
        elif command == "list":
            result = await list_subscriptions(
                session, event, parsed.groups, parsed.privates
            )
        elif command == "show":
            result = await show(session, event, tokens, parsed.groups, parsed.privates)
        elif command == "event":
            if not tokens:
                raise ValueError("用法：/ghp event list|add|remove|set ...")
            operation, *arguments = tokens
            if operation == "list":
                result = await event_list(arguments)
            elif operation in {"add", "remove", "set"}:
                result = await edit_events(
                    session,
                    event,
                    operation,
                    arguments,
                    parsed.groups,
                    parsed.privates,
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
                session,
                event,
                operation,
                arguments,
                parsed.groups,
                parsed.privates,
            )
        elif command in {"pause", "resume"}:
            result = await set_enabled(
                session,
                event,
                command == "resume",
                tokens,
                parsed.groups,
                parsed.privates,
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
    await service.poll_all()


if not plugin_config.github_poller_github_token:
    logger.warning(
        "github_poller 未配置 GitHub Token：插件仍会运行，但只能读取公开仓库，"
        "且未认证 API 通常限制为每小时 60 次请求"
    )
