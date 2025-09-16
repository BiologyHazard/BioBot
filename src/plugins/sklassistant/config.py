from nonebot import get_plugin_config
from pydantic import BaseModel, DirectoryPath, FilePath, NameEmail
from pathlib import Path


class Config(BaseModel):
    skl_name_email: NameEmail
    skl_email_password: str
    skl_email_smtp_host: str = 'smtp.qq.com'
    skl_email_smtp_port: int = 465
    skl_data_path: DirectoryPath = Path('data/sklassistant')
    skl_tokens_file_path: FilePath = skl_data_path / 'tokens.json'
    skland_did: str
    server: str = "127.0.0.1"


plugin_config: Config = get_plugin_config(Config)
# plugin_config.skl_data_path.mkdir(parents=True, exist_ok=True)
# plugin_config.skl_tokens_file_path.parent.mkdir(parents=True, exist_ok=True)
