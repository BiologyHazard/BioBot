from nonebot import logger

from pydantic import BaseModel, PositiveInt, model_validator
from typing import Any, Literal


class Config(BaseModel):
    repeater_group: Literal["all"] | list[Any] = "all"
    repeater_min_message_length: PositiveInt = 1
    repeater_min_message_times: PositiveInt = 2
    repeater_blacklist: list[str] = []

    @model_validator(mode="before")
    @classmethod
    def check_default_values(cls, values):
        for name, field in cls.model_fields.items():
            if name not in values:
                logger.opt(colors=True).warning(f'<b>[复读姬]</> 未发现配置项 <magenta>{name!r}</>, 采用默认值: {field.default!r}')
        return values
