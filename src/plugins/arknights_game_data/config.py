from arknights_game_model.config import Config as ModelConfig
from nonebot import get_plugin_config
from pydantic import Field


class Config(ModelConfig):
    reload_interval_seconds: float = Field(default=30, ge=10)
    """检查游戏数据文件是否更新的间隔，单位为秒。"""


plugin_config = get_plugin_config(Config)
