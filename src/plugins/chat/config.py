from nonebot import get_plugin_config
from pydantic import BaseModel, model_validator
from nonebot import logger


class Config(BaseModel):
    spark_appid: str = ''
    spark_api_secret: str = ''
    spark_api_key: str = ''
    spark_version: str = 'v3.5'
    qwen_api_key: str = ''
    # dashscope_api_key: str | None = None

    @model_validator(mode='before')
    @classmethod
    def check_default_values(cls, values):
        for name, field in cls.model_fields.items():
            if name not in values:
                logger.opt(colors=True).warning(f'<b>[Chat]</> 未发现配置项 <magenta>{name!r}</>, 采用默认值: {field.default!r}')
        return values


plugin_config: Config = get_plugin_config(Config)
# if not plugin_config.spark_appid or not plugin_config.spark_api_secret or not plugin_config.spark_api_key:
#     logger.warning('未设置星火APPID、API_SECRET或API_KEY，插件将无法使用！')
# if not plugin_config.qwen_api_key:
#     logger.warning('未设置通义千问API_KEY，插件将无法使用！')
