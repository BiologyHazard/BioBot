# ruff: noqa: E402

from nonebot import require

require("nonebot_plugin_orm")

from nonebot import get_driver

from . import commands as commands
from .app import add_routes

driver = get_driver()


@driver.on_startup
async def _() -> None:
    add_routes(driver)
