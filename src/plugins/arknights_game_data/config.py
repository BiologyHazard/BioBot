from arknights_game_model.config import Config as ModelConfig
from nonebot import get_driver
from pydantic import Field


class Config(ModelConfig):
    reload_interval_seconds: float = Field(default=30, ge=10)
    """检查游戏数据文件是否更新的间隔。"""


plugin_config = Config(_env_file=(".env", f".env.{get_driver().env}"))  # type: ignore
