from nonebot import get_driver
from pydantic import BaseModel, DirectoryPath, FilePath, NameEmail
from pathlib import Path


class Config(BaseModel):
    skl_name_email: NameEmail
    skl_email_password: str
    skl_email_smtp_host: str = 'smtp.qq.com'
    skl_email_smtp_port: int = 465
    skl_data_path: DirectoryPath = Path('data/sklautosignin')
    skl_tokens_file_path: FilePath = skl_data_path / 'tokens.json'


plugin_config: Config = Config.parse_obj(get_driver().config)
