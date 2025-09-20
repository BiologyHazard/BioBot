from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, FilePath


class Config(BaseModel):
    font_path: FilePath = Path("data/fonts/consola.ttf")


plugin_config: Config = get_plugin_config(Config)
