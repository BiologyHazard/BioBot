from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    github_poller_github_token: str | None = None
    github_poller_poll_interval: float = Field(default=300, ge=10)
    github_poller_user_agent: str = "BioBot"


plugin_config = get_plugin_config(Config)
