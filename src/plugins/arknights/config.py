from arknights_game_model.config import Config
from nonebot import get_driver

plugin_config = Config(_env_file=(".env", f".env.{get_driver().env}"))  # type: ignore
