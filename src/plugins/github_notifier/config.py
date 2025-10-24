from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, FilePath


class Config(BaseModel):
    data_path: FilePath = Path("data/github_notifier/data.json")


plugin_config: Config = get_plugin_config(Config)
