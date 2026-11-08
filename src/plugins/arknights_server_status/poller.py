"""服务器状态状态机：定时探测、停服期间高频轮询、开服通知。"""

import asyncio
import contextlib

from nonebot import get_bots, logger
from nonebot.adapters.onebot.v11 import Bot as BotV11

from .client import ServerStatus, StatusCheckError, client
from .config import plugin_config

_STATUS_LABELS = {
    ServerStatus.OPEN: "已开服",
    ServerStatus.CLOSED: "停机更新中",
    ServerStatus.UNKNOWN: "无法判定",
}


def _label(status: str | None) -> str:
    return _STATUS_LABELS.get(status, "未知") if status else "尚未检查"


class ServerStatusPoller:
    """把「探测结果」变成「可推送的状态变化」。

    - 状态只保存在内存中，进程重启后从「尚未检查」重新开始。
    - 探测失败或结果不可判定时保持已有状态，只记日志。
    - 状态变为停服时启动每 30 秒（可配置）一次的高频轮询。
    - 状态从停服变为开服时返回「需要推送通知」，由调用方在锁外发送。
    """

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._fast_task: asyncio.Task[None] | None = None
        self._status: str | None = None

    @property
    def status(self) -> str | None:
        return self._status

    async def probe(self) -> str:
        """只探测，不改变状态机，供手动查询使用。"""
        async with self._lock:
            return await client.check_status()

    async def poll_and_apply(self) -> None:
        """探测一次并应用状态变化；需要时推送开服通知。"""
        async with self._lock:
            try:
                status = await client.check_status()
            except StatusCheckError as error:
                logger.warning("明日方舟服务器状态探测失败：{}", error)
                return
            logger.debug(
                "明日方舟服务器状态检查结果：{}（上次：{}）",
                _label(status),
                _label(self._status),
            )
            should_notify = self._apply(status)
        if should_notify:
            await notify_server_open()

    def _apply(self, status: str) -> bool:
        """记录新状态，返回是否需要推送开服通知。"""
        if status == ServerStatus.UNKNOWN:
            logger.warning(
                "明日方舟服务器状态无法判定（u8 getToken 返回非预期结果），保持当前状态：{}",
                _label(self._status),
            )
            return False

        previous = self._status
        if previous != status:
            self._status = status
            if status == ServerStatus.CLOSED:
                logger.info(
                    "明日方舟服务器处于停机更新中，改为每 {} 秒检查一次",
                    plugin_config.arknights_server_poll_interval_seconds,
                )
            else:
                logger.info("明日方舟服务器已开服")

        if status == ServerStatus.CLOSED:
            self._start_fast_poll()
            return False

        self._stop_fast_poll()
        return previous == ServerStatus.CLOSED

    def _start_fast_poll(self) -> None:
        if self._fast_task is not None and not self._fast_task.done():
            return
        self._fast_task = asyncio.create_task(self._fast_poll_loop())

    def _stop_fast_poll(self) -> None:
        task = self._fast_task
        self._fast_task = None
        if task is None or task.done():
            return
        if task is asyncio.current_task():
            # 由轮询任务自己检测到开服，循环条件已不成立，无需取消自己。
            return
        task.cancel()

    async def _fast_poll_loop(self) -> None:
        try:
            while self._status == ServerStatus.CLOSED:
                await asyncio.sleep(
                    plugin_config.arknights_server_poll_interval_seconds
                )
                await self.poll_and_apply()
        finally:
            # 任务可能已被新的轮询任务取代，只在仍是自己时才清空句柄。
            if self._fast_task is asyncio.current_task():
                self._fast_task = None

    async def shutdown(self) -> None:
        task = self._fast_task
        self._fast_task = None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        await client.close()


async def notify_server_open() -> None:
    """向 `ARKNIGHTS_SERVER_NOTIFY_GROUPS` 中的每个群推送开服通知。"""
    groups = plugin_config.arknights_server_notify_groups
    if not groups:
        logger.warning(
            "明日方舟已开服，但未配置 ARKNIGHTS_SERVER_NOTIFY_GROUPS，跳过群通知"
        )
        return

    bots = [bot for bot in get_bots().values() if isinstance(bot, BotV11)]
    if not bots:
        logger.warning("明日方舟已开服，但当前没有可用的 OneBot V11 连接，跳过群通知")
        return

    message = plugin_config.arknights_server_notify_message
    for bot in bots:
        for group_id in groups:
            try:
                await bot.send_group_msg(group_id=group_id, message=message)
            except Exception:
                logger.exception("向群 {} 推送开服通知失败", group_id)
    logger.info("已向 {} 个群推送明日方舟开服通知", len(groups))


poller = ServerStatusPoller()
