from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, DirectoryPath, FilePath, PositiveInt


class Config(BaseModel):
    data_path: DirectoryPath = Path('data/autoreply')
    '''加载插件时会建目录，因此该目录原则上存在'''
    font_path: DirectoryPath = Path('data/fonts')
    text_font_path: FilePath = font_path / 'SourceHanSans.otf'


plugin_config: Config = Config.parse_obj(get_driver().config)
plugin_config.data_path.mkdir(parents=True, exist_ok=True)
