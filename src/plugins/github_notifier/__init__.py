import json

from nonebot import get_bots, get_driver, logger
from nonebot.drivers import URL, ASGIMixin, HTTPServerSetup, Request, Response

from .config import plugin_config

background_tasks = set()
driver = get_driver()


async def postreceive(request: Request) -> Response:
    if plugin_config.data_path.is_file():
        data = json.loads(plugin_config.data_path.read_text("utf-8"))
    else:
        data = {}

    repo_name = request.json["repository"]["full_name"]
    if repo_name not in data:
        return Response(200, content="未配置该仓库的通知。")

    lines = []
    lines.append(f"{repo_name} 有新的推送")
    lines.append(f"仓库地址：{request.json['repository']['html_url']}")
    lines.append("________")
    for commit in request.json["commits"]:
        lines.append("")
        lines.append(f"[{commit['timestamp']}] {commit['id']}")
        lines.append(f"提交信息：{commit['message']}")
        lines.append(f"提交地址：{commit['url']}")
        lines.append(f"作者：{commit['author']['name']} <{commit['author']['email']}>")
    text = "\n".join(lines)

    repo_data = data[repo_name]
    for group_id_str in repo_data.get("group", []):
        for bot in get_bots().values():
            try:
                await bot.send_group_msg(group_id=group_id_str, message=text)
                break
            except Exception as e:
                logger.warning(
                    f"Bot {bot} 向群 {group_id_str} 发送 GitHub 通知失败：{e!r}"
                )
        else:
            logger.error(f"没有可用的 Bot 向群 {group_id_str} 发送通知。")

    for user_id_str in repo_data.get("private", []):
        for bot in get_bots().values():
            try:
                await bot.send_private_msg(user_id=user_id_str, message=text)
                break
            except Exception as e:
                logger.warning(
                    f"Bot {bot} 向用户 {user_id_str} 发送 GitHub 通知失败：{e!r}"
                )
        else:
            logger.error(f"没有可用的 Bot 向用户 {user_id_str} 发送通知。")

    return Response(200, content=text)


async def test(request: Request) -> Response:
    lines = []
    for bot_str, bot in get_bots().items():
        lines.append(bot_str)
        lines.append(repr(bot))
        lines.append(repr(bot.__dict__))
        lines.append("")
    return Response(200, content="\n".join(lines))


if not isinstance(driver, ASGIMixin):
    logger.error(f"驱动器 {driver} 不为服务端类型，无法添加路由。")
else:
    driver.setup_http_server(
        HTTPServerSetup(
            path=URL("/postreceive"),
            method="POST",
            name="postreceive",
            handle_func=postreceive,
        )
    )
    driver.setup_http_server(
        HTTPServerSetup(
            path=URL("/postreceive"),
            method="GET",
            name="postreceive-get",
            handle_func=test,
        )
    )
