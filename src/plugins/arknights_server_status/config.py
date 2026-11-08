from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, field_validator


class Config(BaseModel):
    """明日方舟开服检测插件的配置。

    账号凭据二选一：`HYPERGRYPH_TOKEN`（渠道 token），或 `HYPERGRYPH_PHONE` + `HYPERGRYPH_PASSWORD`。
    """

    hypergryph_phone: str | None = None
    hypergryph_password: str | None = None
    hypergryph_token: str | None = None

    arknights_server_notify_groups: list[int] = Field(default_factory=list)
    arknights_server_notify_message: str = "明日方舟开门了！"

    arknights_server_poll_interval_seconds: float = Field(default=30, ge=5)

    arknights_server_data_dir: Path = Field(
        default=Path("data") / "arknights_server_status",
        description="设备标识的落盘目录，相对路径基于工作目录",
    )

    arknights_device_id: str | None = None

    @field_validator(
        "hypergryph_phone",
        "hypergryph_password",
        "hypergryph_token",
        "arknights_device_id",
        mode="before",
    )
    @classmethod
    def _coerce_to_str(cls, value: object) -> object:
        """`.env` 里纯数字的值（如手机号）会被解析成 int，这里统一还原成字符串。"""
        return str(value) if isinstance(value, int) else value

    @property
    def has_password_credentials(self) -> bool:
        return bool(self.hypergryph_phone and self.hypergryph_password)

    @property
    def has_credentials(self) -> bool:
        return bool(self.hypergryph_token) or self.has_password_credentials


plugin_config = get_plugin_config(Config)
