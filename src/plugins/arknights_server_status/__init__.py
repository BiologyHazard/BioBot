# ruff: noqa: E402

"""检查明日方舟官服是否已结束停机更新（开服），并在开服瞬间推送群通知。"""

from nonebot import get_driver, logger, on_command, require

require("nonebot_plugin_apscheduler")

import asyncio

from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from .client import ServerStatus, StatusCheckError
from .config import Config, plugin_config
from .poller import poller

__plugin_meta__ = PluginMetadata(
    name="明日方舟开服检测",
    description="定时检查明日方舟官服是否已结束停机更新（开服），开服时向指定群推送通知",
    usage="发送「开服状态」可手动查询当前服务器状态",
    type="application",
    config=Config,
)

if not plugin_config.has_credentials:
    logger.warning(
        "arknights_server_status 缺少账号凭据：请配置 HYPERGRYPH_TOKEN，"
        "或同时配置 HYPERGRYPH_PHONE 与 HYPERGRYPH_PASSWORD，否则无法检测服务器状态"
    )


@scheduler.scheduled_job(
    "cron",
    minute="0,30",
    second=0,
    id="arknights_server_status_cron",
    max_instances=1,
    coalesce=True,
)
async def scheduled_check() -> None:
    """每个自然小时的 00 分与 30 分各检查一次。"""
    await poller.poll_and_apply()


_startup_task: asyncio.Task[None] | None = None


def _log_startup_failure(task: asyncio.Task[None]) -> None:
    if task.cancelled() or task.exception() is None:
        return
    logger.opt(exception=task.exception()).error("启动时的明日方舟服务器状态探测失败")


@get_driver().on_startup
async def startup_probe() -> None:
    """启动后立即探测一次，补上机器人离线期间可能错过的停服 → 开服跳变。

    探测包含多次网络请求，放到后台任务里执行，避免拖慢启动。
    """
    global _startup_task
    _startup_task = asyncio.create_task(poller.poll_and_apply())
    _startup_task.add_done_callback(_log_startup_failure)


@get_driver().on_shutdown
async def shutdown_poller() -> None:
    await poller.shutdown()


status_command = on_command(
    "开服状态",
    aliases={"方舟开服状态", "方舟开服了吗", "开服了吗"},
)

_STATUS_REPLIES = {
    ServerStatus.OPEN: "明日方舟已开服，可以进游戏了。",
    ServerStatus.CLOSED: "明日方舟仍在停机维护中，尚未开服。",
    ServerStatus.UNKNOWN: "接口返回了非预期结果，暂时无法判定服务器状态，请稍后再试。",
}


@status_command.handle()
async def handle_status() -> None:
    try:
        status = await poller.probe()
    except StatusCheckError as error:
        await status_command.finish(f"查询失败：{error}")
        return
    await status_command.finish(_STATUS_REPLIES[status])
