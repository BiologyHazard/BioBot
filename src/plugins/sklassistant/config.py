from pathlib import Path

from nonebot import get_plugin_config
from pydantic import BaseModel, FilePath, NameEmail


class Config(BaseModel):
    skl_text_font_path: FilePath = Path("data/fonts/SourceHanSansSC-Regular.otf")
    skl_name_email: NameEmail
    skl_email_password: str
    skl_email_smtp_host: str = "smtp.qq.com"
    skl_email_smtp_port: int = 465
    skland_did: str
    skl_origin: list[str]
    skl_link: str = "https://biobot.biohazard.top/BioBot/plugins/sklassistant"
    skl_save_response: bool = False


plugin_config: Config = get_plugin_config(Config)
