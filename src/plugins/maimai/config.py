from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, DirectoryPath, PositiveInt, FilePath

# data_path = Path('data/maimai')
# cover_path = data_path / 'mai/cover'
# pic_path = data_path / 'mai/pic'
# SONGS_PER_PAGE: int = 25


class Config(BaseModel):
    data_path: DirectoryPath = Path('data/maimai')
    '''加载插件时会建目录，因此该目录原则上存在'''
    cover_path: DirectoryPath = data_path / 'mai/cover'
    pic_path: DirectoryPath = data_path / 'mai/pic'
    font_path: DirectoryPath = data_path / 'fonts'
    text_font_path: FilePath = data_path / 'fonts/SourceHanSans.otf'
    songs_per_page: PositiveInt = 25
    # max_show_count: PositiveInt = 192


plugin_config: Config = Config.parse_obj(get_driver().config)
plugin_config.data_path.mkdir(parents=True, exist_ok=True)
plugin_config.cover_path.mkdir(parents=True, exist_ok=True)
