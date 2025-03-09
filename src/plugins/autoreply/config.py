from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, DirectoryPath, FilePath


class Config(BaseModel):
    data_path: DirectoryPath = Path('data/autoreply')
    '''加载插件时会建目录，因此该目录原则上存在'''
    font_path: DirectoryPath = Path('data/fonts')
    text_font_path: FilePath = font_path / 'SourceHanSans.otf'


plugin_config: Config = get_plugin_config(Config)
plugin_config.data_path.mkdir(parents=True, exist_ok=True)
