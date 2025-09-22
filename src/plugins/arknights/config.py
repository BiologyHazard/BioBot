from nonebot import get_plugin_config
from pydantic import BaseModel, DirectoryPath, FilePath


class Config(BaseModel):
    arknights_gamedata_folder: DirectoryPath
    arknights_online_time_path: FilePath
    arknights_yituliu_item_value_path: FilePath


plugin_config: Config = get_plugin_config(Config)
