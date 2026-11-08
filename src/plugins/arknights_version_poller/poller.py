"""轮询明日方舟各平台的版本接口，检测到发版时推送群通知。

状态只保存在内存里：进程重启后以第一次轮询结果为基准，不补发重启前的变更。
"""

import asyncio
import contextlib
from dataclasses import dataclass

import aiohttp
from nonebot import get_bots, logger
from nonebot.adapters.onebot.v11 import Bot as BotV11

from .config import plugin_config

VERSION_URL_TEMPLATE = (
    "https://ak-conf.hypergryph.com/config/prod/official/{platform}/version"
)

#: 每轮按此顺序依次请求，不并发。
PLATFORMS = ("Windows", "Android", "IOS")


class VersionFetchError(Exception):
    """接口不可达或返回了不可用的响应。"""


@dataclass(frozen=True)
class VersionChange:
    """某个平台检测到的版本变化。"""

    platform: str
    content: str


def _one_line(content: str) -> str:
    return " ".join(content.split())


async def fetch_version(session: aiohttp.ClientSession, platform: str) -> str:
    """请求单个平台的版本接口，返回原始响应内容。"""
    url = VERSION_URL_TEMPLATE.format(platform=platform)
    # logger.debug("请求明日方舟 {} 版本接口：{}", platform, url)
    try:
        async with session.get(url) as response:
            body = (await response.text()).strip()
            if response.status != 200:
                raise VersionFetchError(f"HTTP {response.status}")
    except (aiohttp.ClientError, TimeoutError) as error:
        raise VersionFetchError(f"{type(error).__name__}: {error}") from error
    if not body:
        raise VersionFetchError("响应内容为空")
    return body


def build_message(change: VersionChange) -> str:
    return f"明日方舟发包了！\n【{change.platform}】\n{change.content}"


async def notify_changes(changes: list[VersionChange]) -> None:
    """向 `ARKNIGHTS_SERVER_NOTIFY_GROUPS` 中的每个群推送变化通知。"""
    groups = plugin_config.arknights_server_notify_groups
    if not groups:
        logger.warning(
            "明日方舟版本发生变化，但未配置 ARKNIGHTS_SERVER_NOTIFY_GROUPS，跳过群通知"
        )
        return

    bots = [bot for bot in get_bots().values() if isinstance(bot, BotV11)]
    if not bots:
        logger.warning(
            "明日方舟版本发生变化，但当前没有可用的 OneBot V11 连接，跳过群通知"
        )
        return

    for change in changes:
        message = build_message(change)
        for bot in bots:
            for group_id in groups:
                try:
                    await bot.send_group_msg(group_id=group_id, message=message)
                except Exception:
                    logger.exception(
                        "向群 {} 推送明日方舟 {} 发版通知失败",
                        group_id,
                        change.platform,
                    )
    logger.info(
        "已向 {} 个群推送明日方舟发版通知：{}",
        len(groups),
        "、".join(change.platform for change in changes),
    )


class VersionPoller:
    """定时轮询三个平台，把「响应内容变化」变成「群通知」。"""

    def __init__(self) -> None:
        self._last: dict[str, str] = {}
        self._task: asyncio.Task[None] | None = None
        self._session: aiohttp.ClientSession | None = None

    def start(self) -> None:
        if self._task is not None and not self._task.done():
            return
        self._task = asyncio.create_task(self._loop())

    async def _loop(self) -> None:
        while True:
            await self.poll_once()
            await asyncio.sleep(plugin_config.arknights_version_poll_interval_seconds)

    async def poll_once(self) -> None:
        """依次轮询三个平台，发现变化时推送。"""
        session = self._get_session()
        changes: list[VersionChange] = []
        # logger.debug("开始轮询明日方舟版本接口：{}", "、".join(PLATFORMS))
        for platform in PLATFORMS:
            try:
                content = await fetch_version(session, platform)
            except VersionFetchError as error:
                logger.debug(
                    "明日方舟 {} 版本轮询失败：{}", platform, error, exc_info=True
                )
                logger.warning("明日方舟 {} 版本接口请求失败：{}", platform, error)
                continue

            previous = self._last.get(platform)
            self._last[platform] = content
            logger.debug("明日方舟 {} 版本轮询结果：{}", platform, _one_line(content))
            if previous is None:
                logger.info(
                    "记录明日方舟 {} 版本基线：{}", platform, _one_line(content)
                )
            elif previous != content:
                logger.info(
                    "明日方舟 {} 版本发生变化：{} → {}",
                    platform,
                    _one_line(previous),
                    _one_line(content),
                )
                changes.append(VersionChange(platform, content))

        if changes:
            await notify_changes(changes)

    def _get_session(self) -> aiohttp.ClientSession:
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(
                    total=plugin_config.arknights_version_request_timeout
                )
            )
        return self._session

    async def shutdown(self) -> None:
        task = self._task
        self._task = None
        if task is not None and not task.done():
            task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await task
        if self._session is not None and not self._session.closed:
            await self._session.close()
        self._session = None


poller = VersionPoller()
