from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    github_token: str | None = None
    github_poll_interval: int = Field(default=300, ge=10)
    github_poller_data_path: Path = Path("data/github_poller/data.json")
    github_poller_per_page: int = Field(default=30, ge=1, le=100)


plugin_config = get_plugin_config(Config)
