import asyncio
import json
from pathlib import Path

from nonebot import get_app, get_driver, logger
from nonebot.drivers import URL, ASGIMixin, HTTPServerSetup, Request, Response

from .config import plugin_config
from .manager import tokens
from .skland import TOKEN_LENGTH, SKLand, SKLandError, attendance_and_send_email
from .utils import is_base64, is_valid_email

driver = get_driver()
if not isinstance(driver, ASGIMixin):
    logger.error(f"驱动器 {driver} 不为服务端类型，无法添加 CORS 中间件。")
else:
    try:
        from fastapi import FastAPI
        from fastapi.middleware.cors import CORSMiddleware
    except ImportError:
        logger.error("未安装 fastapi，无法添加 CORS 中间件。")
    else:
        app = get_app()
        if isinstance(app, FastAPI):
            app.add_middleware(
                CORSMiddleware,
                allow_origins=[plugin_config.skl_origin],
                allow_methods=["GET", "POST"],
            )


class ValidationError(Exception):
    pass


background_tasks = set()

home_html_content: str | None = None


def get_home_html_content() -> str:
    global home_html_content
    if home_html_content is None:
        home_html_content = (Path(__file__).parent / "html/index.html").read_text(
            "utf-8"
        )
    return home_html_content


async def home(request: Request) -> Response:
    logger.debug(f"有请求：{request!r}")
    return Response(
        status_code=200,
        headers={"Content-Type": "text/html; charset=utf-8"},
        content=get_home_html_content(),
    )


async def commit(request: Request) -> Response:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Access-Control-Allow-Origin": "*",
    }

    def validate_qq(qq: str) -> int:
        if 5 <= len(qq) < 20 and qq.isdigit():
            return int(qq)
        raise ValidationError("QQ号输入错误。")

    def validate_email(email: str) -> str:
        if is_valid_email(email):
            return email
        raise ValidationError("Email输入错误。")

    def validate_token(token: str) -> str:
        if len(token) == TOKEN_LENGTH and is_base64(token):
            return token
        raise ValidationError("token输入错误。")

    logger.debug(f"有请求：{request.__dict__}")

    form = request.json
    try:
        qq = validate_qq(form["qq"])
        email = validate_email(form["email"])
        token = validate_token(form["token"])
    except ValidationError as e:
        return Response(
            status_code=400,
            headers=headers,
            content=json.dumps({"code": 400, "message": str(e), "data": None}),
        )

    try:
        await SKLand().login_by_token(token)
    except SKLandError as e:
        return Response(
            status_code=403,
            headers=headers,
            content=json.dumps(
                {"code": 403, "message": f"绑定森空岛token失败：{e}", "data": None}
            ),
        )

    await tokens.add_item(qq, email, token)

    task = asyncio.create_task(attendance_and_send_email(token, True, email))
    background_tasks.add(task)
    task.add_done_callback(background_tasks.discard)

    return Response(
        status_code=200,
        headers=headers,
        content=json.dumps({"code": 200, "message": "提交成功。", "data": None}),
    )


def on_startup():
    driver = get_driver()
    if not isinstance(driver, ASGIMixin):
        logger.error(f"驱动器 {driver} 不为服务端类型，无法添加路由。")
    else:
        driver.setup_http_server(
            HTTPServerSetup(
                path=URL("/BioBot/plugins/sklassistant"),
                method="GET",
                name="home",
                handle_func=home,
            )
        )
        driver.setup_http_server(
            HTTPServerSetup(
                path=URL("/BioBot/plugins/sklassistant"),
                method="POST",
                name="commit",
                handle_func=commit,
            )
        )
