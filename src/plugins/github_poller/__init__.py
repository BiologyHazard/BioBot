"""GitHub repository polling notifier.

This plugin is intentionally separate from ``github_notifier``.  It uses the
GitHub REST API and sends text messages only; no webhook, HTML renderer, or
image generator is involved.
"""

from __future__ import annotations

import asyncio
import json
from datetime import UTC, datetime
from typing import Annotated, Any

from githubkit import GitHub
from nonebot import get_bots, get_driver, logger, on_command, require
from nonebot.adapters.onebot.v11 import GroupMessageEvent, Message, MessageEvent
from nonebot.params import CommandArg
from nonebot.permission import SUPERUSER
from nonebot.plugin import PluginMetadata

from .config import Config, plugin_config

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name="GitHub 轮询通知",
    description="通过 GitHub REST API 轮询仓库动态并发送纯文本通知",
    usage="TODO",
    type="application",
    config=Config,
)


repo_add = on_command("订阅仓库", permission=SUPERUSER)
repo_delete = on_command("取消订阅仓库", permission=SUPERUSER)
repo_show = on_command("查看订阅仓库", permission=SUPERUSER)
repo_refresh = on_command("刷新订阅仓库", permission=SUPERUSER)
api_usage_cmd = on_command("检查ghapi用量", permission=SUPERUSER)

github = GitHub(
    auth=plugin_config.github_poller_github_token,
    user_agent=plugin_config.github_poller_user_agent,
)
