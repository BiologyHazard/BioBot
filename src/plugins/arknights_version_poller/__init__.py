"""轮询明日方舟 Windows / Android / IOS 的版本接口，检测到发包时推送群通知。"""

from nonebot import get_driver
from nonebot.log import logger
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config
from .poller import poller

__plugin_meta__ = PluginMetadata(
    name="明日方舟发版检测",
    description="定时轮询明日方舟各平台的版本接口，检测到版本或资源包变化时向指定群推送通知",
    usage="无需指令，插件在后台每 20 秒依次轮询一次并自动推送",
    type="application",
    config=Config,
)

if not plugin_config.arknights_version_notify_groups:
    logger.warning(
        "arknights_version_poller 未配置 ARKNIGHTS_VERSION_NOTIFY_GROUPS，"
        "检测到版本变化时只记录日志，不推送群通知"
    )


@get_driver().on_startup
async def startup_poller() -> None:
    poller.start()


@get_driver().on_shutdown
async def shutdown_poller() -> None:
    await poller.shutdown()
