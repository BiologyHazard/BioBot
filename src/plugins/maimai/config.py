from pathlib import Path

from nonebot import get_driver
from pydantic import BaseModel, DirectoryPath, PositiveInt

# data_path = Path('data/maimai')
# cover_path = data_path / 'mai/cover'
# pic_path = data_path / 'mai/pic'
# SONGS_PER_PAGE: int = 25


class Config(BaseModel):
    data_path: DirectoryPath = Path('data/maimai')
    '''加载插件时会建目录，因此该目录原则上存在'''
    cover_path: Path = data_path / 'mai/cover'
    pic_path: Path = data_path / 'mai/pic'
    text_font_path: Path = data_path / 'fonts/SourceHanMonoSC-Regular.otf'
    songs_per_page: PositiveInt = 25


plugin_config: Config = Config.parse_obj(get_driver().config)
plugin_config.data_path.mkdir(parents=True, exist_ok=True)
plugin_config.cover_path.mkdir(parents=True, exist_ok=True)
