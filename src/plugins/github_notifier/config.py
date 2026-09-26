from urllib.parse import urlsplit
from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """GitHub webhook 通知插件的配置。"""

    github_notifier_webhook_payload_url: str
    github_notifier_batch_window_seconds: float = Field(default=60, gt=0)
    github_notifier_filter_config: Path | None = None

    @field_validator("github_notifier_webhook_payload_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        """确保 webhook 基础地址是没有查询参数的 HTTP(S) URL。"""
        parsed = urlsplit(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("github_notifier_webhook_payload_url 必须是 HTTP(S) URL")
        if parsed.query or parsed.fragment:
            raise ValueError("webhook URL 不得包含查询参数或片段")
        return value


plugin_config: Config = get_plugin_config(Config)
