import asyncio
import json
from typing import Any

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
                allow_origins=plugin_config.skl_origin,
                allow_methods=["GET", "POST"],
            )
        else:
            logger.error(f"驱动器 {driver} 不是 FastAPI 实例，无法添加 CORS 中间件。")


class ValidationError(Exception):
    pass


background_tasks = set()


async def home(request: Request) -> Response:
    logger.debug(f"有请求：{request!r}")
    return Response(
        status_code=302,
        headers={"Location": "https://riic.biohazard.top/sklassistant"},
    )


async def commit(request: Request) -> Response:
    headers = {
        "Content-Type": "application/json; charset=utf-8",
    }

    def validate_qq(qq: Any) -> int:
        if isinstance(qq, str) and 5 <= len(qq) < 20 and qq.isdigit():
            return int(qq)
        raise ValidationError("QQ 号输入错误。")

    def validate_email(email: Any) -> str:
        if isinstance(email, str) and is_valid_email(email):
            return email
        raise ValidationError("Email 输入错误。")

    def validate_token(token: Any) -> str:
        if isinstance(token, str) and len(token) == TOKEN_LENGTH and is_base64(token):
            return token
        raise ValidationError("token 输入错误。")

    def validate_remind(remind: Any) -> bool:
        if isinstance(remind, bool):
            return remind
        if remind == "on":
            return True
        raise ValidationError("remind 输入错误。")

    logger.debug(f"有请求：{request.__dict__}")

    form = request.json
    try:
        if not isinstance(form, dict):
            raise ValidationError("请求体格式错误，应为 JSON 对象。")
        qq = validate_qq(form.get("qq", None))
        email = validate_email(form.get("email", None))
        token = validate_token(form.get("token", None))
        remind = validate_remind(form.get("remind", False))
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
                {"code": 403, "message": f"绑定森空岛 token 失败：{e}", "data": None}
            ),
        )

    await tokens.add_item(qq, email, token)

    task = asyncio.create_task(attendance_and_send_email(token, remind, email))
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
