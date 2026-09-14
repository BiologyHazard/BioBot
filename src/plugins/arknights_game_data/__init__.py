# ruff: noqa: E402

from __future__ import annotations

from nonebot import require

require("nonebot_plugin_apscheduler")

import asyncio

from arknights_game_model.game_data import game_data
from nonebot import get_driver, logger
from nonebot.plugin import PluginMetadata
from nonebot_plugin_apscheduler import scheduler

from .config import Config, plugin_config
from .reloader import DataChangedDuringReloadError, GameDataReloader

__plugin_meta__ = PluginMetadata(
    name="明日方舟游戏数据",
    description="为明日方舟插件加载并热更新共享游戏数据",
    usage="内部插件，无用户命令",
    type="library",
    config=Config,
)

game_data_reloader = GameDataReloader(plugin_config)


@get_driver().on_startup
async def load_initial_game_data() -> None:
    """在处理消息前加载首份数据快照。

    若恰逢解包仓库写入，则短暂重试；其他读取或校验错误会直接阻止启动，避免
    业务插件在没有有效数据的状态下运行。
    """
    for attempt in range(3):
        try:
            await game_data_reloader.reload_if_changed(force=True)
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
async def refresh_game_data(*, force: bool = False) -> bool:
    """检查并刷新共享快照，失败时保留上一份有效数据。

    Args:
        force: 是否忽略文件指纹并强制重载。

    Returns:
        成功发布新快照时为 ``True``；无变化或刷新失败时为 ``False``。
    """
    try:
        changed = await game_data_reloader.reload_if_changed(force=force)
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
