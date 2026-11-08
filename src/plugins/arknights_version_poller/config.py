from nonebot import get_plugin_config
from pydantic import BaseModel, Field


class Config(BaseModel):
    """明日方舟发版检测插件的配置。

    推送目标与 `arknights_server_status` 共用 `ARKNIGHTS_SERVER_NOTIFY_GROUPS`。
    """

    arknights_server_notify_groups: list[int] = Field(
        default_factory=list,
        description="接收发版通知的群号，与开服检测插件共用同一个配置项",
    )

    arknights_version_poll_interval_seconds: float = Field(
        default=20,
        ge=5,
        description="每一轮依次轮询 Windows / Android / IOS 三个接口的间隔（秒）",
    )

    arknights_version_request_timeout: float = Field(
        default=15,
        ge=1,
        description="单个版本接口请求的超时时间（秒）",
    )


plugin_config = get_plugin_config(Config)
