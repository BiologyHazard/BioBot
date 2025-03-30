from nonebot import get_plugin_config
from pydantic import BaseModel, PositiveInt, PositiveFloat


class Config(BaseModel):
    biliinfo_sleep_time: PositiveFloat = 2.0
    biliinfo_show_comments: bool = False
    biliinfo_max_count: PositiveInt = 5


plugin_config: Config = get_plugin_config(Config)
