"""GitHub repository polling notifier.

This plugin is intentionally separate from ``github_notifier``.  It uses the
GitHub REST API and sends text messages only; no webhook, HTML renderer, or
image generator is involved.
"""

from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from githubkit import GitHub
from nonebot import get_bots, get_driver, logger, on_command, require
from nonebot.adapters.onebot.v11 import GroupMessageEvent, MessageEvent
from nonebot.params import CommandArg
from nonebot.plugin import PluginMetadata
from nonebot.adapters.onebot.v11 import Message

from .config import plugin_config

require("nonebot_plugin_apscheduler")
from nonebot_plugin_apscheduler import scheduler  # noqa: E402

__plugin_meta__ = PluginMetadata(
    name="GitHub 轮询通知",
    description="通过 GitHub REST API 轮询仓库动态并发送纯文本通知",
    usage="/repo.add owner/repo [group_id]",
    type="application",
    homepage="https://github.com/HTony03/nonebot_plugin_github_release_notifier",
    config=plugin_config.__class__,
)

driver = get_driver()
poll_lock = asyncio.Lock()
api_usage: dict[str, int] = {"requests": 0, "last_remaining": -1}

EVENTS = {"commit", "issue", "pull_request", "release", "issue_comment"}
EVENT_ALIASES = {"commits": "commit", "issues": "issue", "pr": "pull_request", "prs": "pull_request", "pulls": "pull_request", "release": "release", "comment": "issue_comment"}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _load() -> dict[str, Any]:
    path = plugin_config.github_poller_data_path
    if not path.is_file():
        return {}
    try:
        data = json.loads(path.read_text("utf-8"))
        return data if isinstance(data, dict) else {}
    except (OSError, ValueError) as exc:
        logger.error(f"读取 GitHub 轮询数据失败：{exc!r}")
        return {}


def _save(data: dict[str, Any]) -> None:
    path = plugin_config.github_poller_data_path
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(path.suffix + ".tmp")
    temp.write_text(json.dumps(data, ensure_ascii=False, indent=4), "utf-8")
    temp.replace(path)


def _repo_config(data: dict[str, Any], repo: str) -> dict[str, Any]:
    value = data.setdefault(repo, {})
    value.setdefault("group", [])
    value.setdefault("private", [])
    value.setdefault("events", sorted(EVENTS))
    value.setdefault("state", {})
    return value


def _targets(config: dict[str, Any]) -> tuple[list[int], list[int]]:
    return ([int(x) for x in config.get("group", [])], [int(x) for x in config.get("private", [])])


async def _send(text: str, config: dict[str, Any]) -> None:
    groups, users = _targets(config)
    for bot in list(get_bots().values()):
        for group_id in groups:
            try:
                await bot.send_group_msg(group_id=group_id, message=text)
            except Exception as exc:
                logger.warning(f"发送 GitHub 群通知失败（{group_id}）：{exc!r}")
        for user_id in users:
            try:
                await bot.send_private_msg(user_id=user_id, message=text)
            except Exception as exc:
                logger.warning(f"发送 GitHub 私聊通知失败（{user_id}）：{exc!r}")


github = GitHub(plugin_config.github_token) if plugin_config.github_token else GitHub()


def _dump(value: Any) -> Any:
    """Convert githubkit's typed Pydantic models to formatter dictionaries."""
    if isinstance(value, list):
        return [_dump(item) for item in value]
    if hasattr(value, "model_dump"):
        return value.model_dump(mode="json", exclude_none=False)
    return value


async def _get(method: Any, params: dict[str, Any]) -> list[dict[str, Any]]:
    response = await method(**params)
    api_usage["requests"] += 1
    remaining = response.headers.get("x-ratelimit-remaining")
    if remaining is not None:
        api_usage["last_remaining"] = int(remaining)
    payload = _dump(response.parsed_data)
    return payload if isinstance(payload, list) else []


def _iso(value: str | None) -> str:
    return value or ""


def _format_event(repo: str, kind: str, item: dict[str, Any]) -> str:
    repository_url = item.get("html_url", f"https://github.com/{repo}")
    if kind == "commit":
        commit = item.get("commit", {})
        author = (commit.get("author") or {}).get("name") or (item.get("author") or {}).get("login") or "未知"
        message = (commit.get("message") or "无提交信息").splitlines()[0]
        return f"GitHub Commit\n仓库：{repo}\n作者：{author}\n信息：{message}\n地址：{repository_url}"
    if kind == "release":
        return f"GitHub Release\n仓库：{repo}\n版本：{item.get('tag_name', item.get('name', '未知'))}\n作者：{(item.get('author') or {}).get('login', '未知')}\n地址：{repository_url}"
    if kind == "issue_comment":
        body = (item.get("body") or "无评论内容").splitlines()[0][:160]
        return f"GitHub Issue/PR 评论\n仓库：{repo}\n#{item.get('issue_number', '?')} {body}\n作者：{(item.get('user') or {}).get('login', '未知')}\n地址：{repository_url}"
    title = item.get("title", "无标题")
    author = (item.get("user") or {}).get("login", "未知")
    kind_name = "Pull Request" if kind == "pull_request" else "Issue"
    return f"GitHub {kind_name}\n仓库：{repo}\n#{item.get('number', '?')} {title}\n作者：{author}\n状态：{item.get('state', '未知')}\n地址：{repository_url}"


async def _poll_repo(repo: str, config: dict[str, Any]) -> list[str]:
    state = config.setdefault("state", {})
    events = set(config.get("events", sorted(EVENTS))) & EVENTS
    found: list[tuple[str, dict[str, Any], str]] = []
    owner, name = repo.split("/", 1)
    page = plugin_config.github_poller_per_page

    endpoints = {
        "commit": (github.rest.repos.async_list_commits, "sha", "commit.author.date", {"owner": owner, "repo": name, "per_page": page}),
        "issue": (github.rest.issues.async_list_for_repo, "id", "updated_at", {"owner": owner, "repo": name, "per_page": page, "sort": "updated", "direction": "desc", "state": "all"}),
        "pull_request": (github.rest.pulls.async_list, "id", "updated_at", {"owner": owner, "repo": name, "per_page": page, "sort": "updated", "direction": "desc", "state": "all"}),
        "release": (github.rest.repos.async_list_releases, "id", "published_at", {"owner": owner, "repo": name, "per_page": page}),
        "issue_comment": (github.rest.issues.async_list_comments_for_repo, "id", "updated_at", {"owner": owner, "repo": name, "per_page": page, "sort": "updated", "direction": "desc"}),
    }
    for kind in events:
        endpoint, id_key, time_key, params = endpoints[kind]
        items = await _get(endpoint, params)
        if not isinstance(items, list):
            continue
        current = state.setdefault(kind, {})
        new_items: list[dict[str, Any]] = []
        for item in items:
            # /issues includes PRs; do not emit those twice.
            if kind == "issue" and "pull_request" in item:
                continue
            key = str(item.get(id_key, ""))
            stamp = _iso(item.get(time_key))
            if not key:
                continue
            if key in current and current[key] >= stamp:
                continue
            current[key] = stamp
            if state.get("initialized"):
                new_items.append(item)
        if state.get("initialized"):
            found.extend((kind, item, _format_event(repo, kind, item)) for item in new_items)
    state["initialized"] = True
    state["last_poll"] = _now()
    return [message for _, _, message in sorted(found, key=lambda value: value[1].get("updated_at", value[1].get("published_at", "")))]


async def poll_all() -> None:
    async with poll_lock:
        data = _load()
        if not data:
            return
        for repo, config in data.items():
            try:
                messages = await _poll_repo(repo, _repo_config(data, repo))
                for message in messages:
                    await _send(message, config)
            except Exception as exc:
                logger.warning(f"轮询 GitHub 仓库 {repo} 失败：{exc!r}")
        _save(data)


def _arg_text(arg: Message | None) -> str:
    return str(arg).strip() if arg else ""


async def _is_admin(event: MessageEvent) -> bool:
    if not isinstance(event, GroupMessageEvent):
        return True
    return event.sender.role in {"admin", "owner"} or str(event.get_user_id()) in {str(x) for x in driver.config.superusers}


repo_add = on_command("repo.add", aliases={"add_group_repo"}, priority=5, block=True)
@repo_add.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if not await _is_admin(event):
        await repo_add.finish("只有群管理员或超级用户可以配置仓库。")
    parts = _arg_text(arg).split()
    if not parts or parts[0].count("/") != 1:
        await repo_add.finish("用法：/repo.add owner/repo [group_id]")
    repo = parts[0]
    target = parts[1] if len(parts) > 1 else (str(event.group_id) if isinstance(event, GroupMessageEvent) else "")
    if not target:
        await repo_add.finish("私聊添加时请指定群号：/repo.add owner/repo group_id")
    data = _load(); config = _repo_config(data, repo)
    field = "group" if isinstance(event, GroupMessageEvent) or target.isdigit() else "private"
    if target not in config[field]: config[field].append(target)
    _save(data)
    await repo_add.finish(f"已添加 {repo} 的 {field} 通知目标。首次同步不会推送历史动态。")


repo_delete = on_command("repo.delete", aliases={"repo.del", "del_group_repo"}, priority=5, block=True)
@repo_delete.handle()
async def _(event: MessageEvent, arg: Message = CommandArg()):
    if not await _is_admin(event): await repo_delete.finish("只有群管理员或超级用户可以配置仓库。")
    repo = _arg_text(arg).split()[0] if _arg_text(arg) else ""
    data = _load()
    if repo not in data: await repo_delete.finish("未找到该仓库。")
    data.pop(repo); _save(data); await repo_delete.finish(f"已删除 {repo}。")


repo_show = on_command("repo.show", aliases={"show_group_repo"}, priority=5, block=True)
@repo_show.handle()
async def _(arg: Message = CommandArg()):
    data = _load()
    if not data: await repo_show.finish("尚未配置 GitHub 仓库。")
    await repo_show.finish("\n".join(f"{repo} -> 群：{', '.join(map(str, cfg.get('group', [])))}；私聊：{', '.join(map(str, cfg.get('private', [])))}" for repo, cfg in data.items()))


repo_refresh = on_command("repo.refresh", aliases={"refresh_group_repo"}, priority=5, block=True)
@repo_refresh.handle()
async def _():
    await poll_all(); await repo_refresh.finish("GitHub 状态刷新完成。")


api_usage_cmd = on_command("check_api_usage", priority=5, block=True)
@api_usage_cmd.handle()
async def _():
    await api_usage_cmd.finish(f"本进程已请求 GitHub API {api_usage['requests']} 次；剩余额度：{api_usage['last_remaining']}")


@driver.on_startup
async def _startup() -> None:
    await poll_all()


@scheduler.scheduled_job("interval", seconds=plugin_config.github_poll_interval, id="github_poller")
async def _scheduled_poll() -> None:
    await poll_all()
