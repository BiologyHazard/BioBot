from pathlib import Path

from nonebot import logger
from quart import Quart, request

from .manager import tokens
from .skland import TOKEN_LENGTH, SKLSignInError, get_grant_code, sign_in_and_send_email
from .utils import is_base64, is_valid_email


class ValidationError(Exception):
    pass


app = Quart(__name__)

home_html_content = None


@app.get("/")
async def home() -> str:
    global home_html_content
    if True or home_html_content is None:
        home_html_content = (Path(__file__).parent / 'html/home.html').read_text()
    return home_html_content


@app.post("/")
async def commit() -> str:
    def validate_qq(qq: str) -> int:
        if 5 <= len(qq) < 20 and qq.isdigit():
            return int(qq)
        raise ValidationError('QQ号输入错误。')

    def validate_email(email: str) -> str:
        if is_valid_email(email):
            return email
        raise ValidationError('Email输入错误。')

    def validate_token(token: str) -> str:
        if len(token) == TOKEN_LENGTH and is_base64(token):
            return token
        raise ValidationError('token输入错误。')

    form = await request.form
    logger.info(f'有提交{form}')
    try:
        qq = validate_qq(form['qq'])
        email = validate_email(form['email'])
        token = validate_token(form['token'])
    except ValidationError as e:
        return str(e)

    try:
        await get_grant_code(token)
    except SKLSignInError as e:
        return f'绑定森空岛token失败：{e!r}'

    tokens.add_item(qq, email, token)
    await sign_in_and_send_email(token, True, email)
    return '提交成功'
