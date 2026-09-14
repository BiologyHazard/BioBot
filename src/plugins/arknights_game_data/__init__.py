"""Shared, hot-reloadable game data for the Arknights plugins."""

from __future__ import annotations

import asyncio

from nonebot import get_driver, logger, require
from nonebot.plugin import PluginMetadata

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

from arknights_game_model.game_data import game_data  # noqa: E402

from .config import Config, plugin_config  # noqa: E402
from .reloader import (  # noqa: E402
    DataChangedDuringReloadError,
    GameDataReloader,
)

__plugin_meta__ = PluginMetadata(
    name="明日方舟游戏数据",
    description="为明日方舟插件加载并热更新共享游戏数据",
    usage="内部插件，无用户命令",
    type="library",
    config=Config,
)

reloader = GameDataReloader(plugin_config)


async def refresh_game_data(*, force: bool = False) -> bool:
    """Refresh the shared snapshot and retain the old one if loading fails."""
    try:
        changed = await reloader.reload_if_changed(force=force)
    except Exception:
        logger.exception("明日方舟游戏数据热更新失败，将继续使用上一份有效数据")
        return False

    if changed:
        logger.info(
            "明日方舟游戏数据已更新：{} 名干员，{} 种物品",
            len(game_data.characters),
            len(game_data.items),
        )
    return changed


@get_driver().on_startup
async def load_initial_game_data() -> None:
    # There is no valid previous snapshot during startup, so a failure must stop
    # startup instead of leaving the singleton half-initialized.
    for attempt in range(3):
        try:
            await reloader.reload_if_changed(force=True)
            break
        except DataChangedDuringReloadError:
            if attempt == 2:
                raise
            await asyncio.sleep(1)
    logger.info(
        "明日方舟游戏数据加载完成：{} 名干员，{} 种物品",
        len(game_data.characters),
        len(game_data.items),
    )


@scheduler.scheduled_job(
    "interval",
    seconds=plugin_config.reload_interval_seconds,
    id="arknights_game_data_hot_reload",
    max_instances=1,
    coalesce=True,
)
async def poll_game_data_updates() -> None:
    await refresh_game_data()
