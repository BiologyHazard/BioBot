from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, DirectoryPath, PositiveInt, FilePath


class Config(BaseModel):
    data_path: DirectoryPath = Path('data/maimai')
    '''加载插件时会建目录，因此该目录原则上存在'''
    cover_path: DirectoryPath = data_path / 'mai/cover'
    pic_path: DirectoryPath = data_path / 'mai/pic'
    chart_path: DirectoryPath = data_path / 'charts'
    font_path: DirectoryPath = Path('data/fonts')
    text_font_path: FilePath = font_path / 'SourceHanSans.otf'
    songs_per_page: PositiveInt = 25


plugin_config: Config = Config.parse_obj(get_driver().config)
plugin_config.data_path.mkdir(parents=True, exist_ok=True)
plugin_config.cover_path.mkdir(parents=True, exist_ok=True)
