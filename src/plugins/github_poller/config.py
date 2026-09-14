from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    github_poller_github_token: str | None = None
    github_poller_poll_interval: float = Field(default=300, ge=10)
    github_poller_user_agent: str = "BioBot"
    github_poller_per_page: int = Field(default=100, ge=1, le=100)
    github_poller_max_pages: int = Field(default=10, ge=1, le=100)
    github_poller_max_events_per_message: int = Field(default=10, ge=1, le=100)
    github_poller_max_message_length: int = Field(default=3500, ge=256)
    github_poller_delivery_max_attempts: int = Field(default=8, ge=1)
    github_poller_request_timeout: float = Field(default=30, ge=1)


plugin_config = get_plugin_config(Config)
