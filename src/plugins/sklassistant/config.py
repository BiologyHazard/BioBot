from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, FilePath, NameEmail


class Config(BaseModel):
    skl_text_font_path: FilePath = Path("data/fonts/SourceHanSansSC-Regular.otf")
    skl_name_email: NameEmail
    skl_email_password: str
    skl_email_smtp_host: str = "smtp.qq.com"
    skl_email_smtp_port: int = 465
    skl_tokens_file_path: FilePath = Path("data/sklassistant/tokens.json")
    skland_did: str
    skl_origin: str


plugin_config: Config = get_plugin_config(Config)
plugin_config.skl_tokens_file_path.parent.mkdir(parents=True, exist_ok=True)
