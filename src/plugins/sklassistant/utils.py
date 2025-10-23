import re


def is_base64(s: str) -> bool:
    pattern = (
        r"^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+/]{3}=|[A-Za-z0-9+/]{2}==)$"
    )
    return re.match(pattern, s) is not None


def is_valid_email(s) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return re.match(pattern, s) is not None


def get_qq_mail_address(qq: int) -> str:
    return f"{qq}@qq.com"
