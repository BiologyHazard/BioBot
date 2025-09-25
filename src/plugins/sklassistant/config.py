from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, Field, FilePath, NameEmail


class Config(BaseModel):
    skl_text_font_path: FilePath = Path("data/fonts/SourceHanSansSC-Regular.otf")
    skl_name_email: NameEmail
    skl_email_password: str
    skl_email_smtp_host: str = "smtp.qq.com"
    skl_email_smtp_port: int = 465
    skl_tokens_file_path: FilePath = Path("data/sklassistant/tokens.json")
    skland_did: str
    skl_server_host: str
    skl_quart_host: str = "0.0.0.0"
    skl_quart_port: int = Field(default=5000, ge=1, le=65535)


plugin_config: Config = get_plugin_config(Config)
plugin_config.skl_tokens_file_path.parent.mkdir(parents=True, exist_ok=True)
