from nonebot import get_driver
from pydantic import BaseModel
from nonebot import logger


class Config(BaseModel):
    spark_appid: str = ''
    spark_api_secret: str = ''
    spark_api_key: str = ''
    spark_version: str = 'v3.5'
    qwen_api_key: str = ''


plugin_config: Config = Config.parse_obj(get_driver().config)
if not plugin_config.spark_appid or not plugin_config.spark_api_secret or not plugin_config.spark_api_key:
    logger.warning('未设置星火APPID、API_SECRET或API_KEY，插件将无法使用！')
if not plugin_config.qwen_api_key:
    logger.warning('未设置通义千问API_KEY，插件将无法使用！')
