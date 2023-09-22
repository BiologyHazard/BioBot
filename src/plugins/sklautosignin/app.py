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


@app.get("/BioBot/plugins/sklautosignin/")
async def home() -> str:
    global home_html_content
    if True or home_html_content is None:
        home_html_content = (Path(__file__).parent / 'html/index.html').read_text()
    return home_html_content


@app.post("/BioBot/plugins/sklautosignin/")
async def commit():
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
        return {
            'code': 400,
            'message': str(e),
            'data': None
        }, 400

    try:
        await get_grant_code(token)
    except SKLSignInError as e:
        return {
            'code': 403,
            'message': f'绑定森空岛token失败：{e}',
            'data': None
        }, 403

    tokens.add_item(qq, email, token)

    # await sign_in_and_send_email(token, True, email)
    app.add_background_task(sign_in_and_send_email, token, True, email)

    return {
        'code': 200,
        'message': f'提交成功。',
        'data': None
    }, 200
