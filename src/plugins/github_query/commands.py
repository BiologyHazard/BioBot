"""QQ command for read-only GitHub repository queries."""

from __future__ import annotations

import asyncio
import sys
from argparse import ArgumentTypeError
from datetime import datetime
from typing import Annotated, Any, Literal

from githubkit import GitHub
from githubkit.exception import (
    GitHubException,
    RateLimitExceeded,
    RequestFailed,
    RequestTimeout,
)
from nonebot import logger, on_shell_command
from nonebot.adapters.onebot.v11 import Bot, MessageEvent
from nonebot.exception import ParserExit
from nonebot.params import ShellCommandArgs
from nonebot.permission import SUPERUSER
from nonebot.rule import ArgumentParser, Namespace

from .config import plugin_config
from .query import GitHubItem, GitHubQuery

QueryKind = Literal["all", "pr", "issue"]


def repository_name(value: str) -> tuple[str, str]:
    """Normalize owner/repo and common GitHub repository URLs."""
    value = value.strip().rstrip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    value = value.removesuffix(".git")
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ArgumentTypeError("仓库格式应为 owner/repo 或 GitHub 仓库 URL")
    return parts[0], parts[1]


def positive_limit(value: str) -> int:
    try:
        limit = int(value)
    except ValueError as exc:
        raise ArgumentTypeError("limit 必须是正整数") from exc
    if limit < 1:
        raise ArgumentTypeError("limit 必须是正整数")
    return limit


class NoColorArgumentParser(ArgumentParser):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        if sys.version_info >= (3, 14):
            kwargs.setdefault("color", False)
        super().__init__(*args, **kwargs)


def _add_list_arguments(parser: ArgumentParser) -> None:
    parser.add_argument("repository", type=repository_name, metavar="OWNER/REPO")
    parser.add_argument(
        "--limit",
        type=positive_limit,
        default=plugin_config.github_query_default_limit,
        metavar="N",
        help="每类事项最多显示多少条",
    )


parser = NoColorArgumentParser(
    prog="gh", description="查询 GitHub 仓库中未关闭的 PR 和 Issue"
)
commands = parser.add_subparsers(dest="command", required=True, metavar="COMMAND")

list_parser = commands.add_parser("list", help="同时列出 PR 和 Issue")
_add_list_arguments(list_parser)

for kind, label in (("pr", "PR"), ("issue", "Issue")):
    kind_parser = commands.add_parser(kind, help=f"查询未关闭的 {label}")
    operations = kind_parser.add_subparsers(
        dest="operation", required=True, metavar="COMMAND"
    )
    kind_list_parser = operations.add_parser("list", help=f"列出未关闭的 {label}")
    _add_list_arguments(kind_list_parser)


github = GitHub(
    auth=plugin_config.github_query_github_token,
    user_agent="BioBot",
    timeout=plugin_config.github_query_request_timeout,
    http_cache=False,
    auto_retry=False,
)
query = GitHubQuery(github, max_pages=plugin_config.github_query_max_pages)

gh = on_shell_command("gh", parser=parser, block=True, priority=5)


@gh.handle()
async def handle_parser_exit(
    parser_exit: Annotated[ParserExit, ShellCommandArgs()],
) -> None:
    await gh.finish(parser_exit.message)


@gh.handle()
async def handle_gh(
    bot: Bot,
    event: MessageEvent,
    args: Annotated[Namespace, ShellCommandArgs()],
) -> None:
    try:
        limit = args.limit
        if limit > plugin_config.github_query_max_limit:
            raise ValueError(f"limit 不能超过 {plugin_config.github_query_max_limit}")
        owner, repo = args.repository
        repository = await query.repository(owner, repo)
        if repository.private and not await SUPERUSER(bot, event):
            raise ValueError("私有仓库仅限机器人超级用户查询")

        kind: QueryKind = args.command if args.command in {"pr", "issue"} else "all"
        pulls: list[GitHubItem] | None = None
        issues: list[GitHubItem] | None = None
        fetch_limit = limit + 1
        if kind == "all":
            pulls, issues = await asyncio.gather(
                query.open_pull_requests(owner, repo, limit=fetch_limit),
                query.open_issues(owner, repo, limit=fetch_limit),
            )
        elif kind == "pr":
            pulls = await query.open_pull_requests(owner, repo, limit=fetch_limit)
        else:
            issues = await query.open_issues(owner, repo, limit=fetch_limit)

        await gh.finish(format_result(repository.full_name, pulls, issues, limit))
    except ValueError as exc:
        await gh.finish(f"参数错误：{exc}")
    except RateLimitExceeded:
        await gh.finish("GitHub API 请求次数已达到限制，请稍后再试")
    except RequestTimeout:
        await gh.finish("GitHub API 请求超时，请稍后再试")
    except RequestFailed as exc:
        status = exc.response.raw_response.status_code
        if status == 404:
            message = "仓库不存在，或机器人没有访问权限"
        elif status in {401, 403}:
            message = "GitHub 拒绝了查询，请检查访问权限或稍后再试"
        else:
            message = f"GitHub API 查询失败（HTTP {status}）"
        await gh.finish(message)
    except GitHubException:
        logger.exception("执行 GitHub 查询命令失败")
        await gh.finish("GitHub 查询失败，请稍后再试")


def format_result(
    repository: str,
    pulls: list[GitHubItem] | None,
    issues: list[GitHubItem] | None,
    limit: int,
) -> str:
    """Format query results as the agreed multiline QQ text."""
    sections = [repository]
    truncated = False
    if pulls is not None:
        visible = pulls[:limit]
        truncated |= len(pulls) > limit
        sections.append(_format_section("PR", visible))
    if issues is not None:
        visible = issues[:limit]
        truncated |= len(issues) > limit
        sections.append(_format_section("Issue", visible))
    if truncated:
        sections.append(f"结果较多，每类仅显示前 {limit} 条。")
    return "\n\n".join(sections)


def _format_section(kind: Literal["PR", "Issue"], items: list[GitHubItem]) -> str:
    if not items:
        return f"未关闭 {kind}：无"
    cards = [f"未关闭 {kind}：{len(items)}"]
    cards.extend(_format_item(kind, item) for item in items)
    return "\n\n".join(cards)


def _format_item(kind: Literal["PR", "Issue"], item: GitHubItem) -> str:
    markers = f"[{kind} #{item.number}]"
    if item.draft:
        markers += " [草稿]"
    lines = [markers, _single_line(item.title, 80)]
    if item.labels:
        lines.append(
            "标签：" + "、".join(_single_line(label, 40) for label in item.labels)
        )
    if item.author:
        lines.append(f"作者：@{_single_line(item.author, 40)}")
    if item.assignees:
        assignees = "、".join(f"@{_single_line(name, 40)}" for name in item.assignees)
        lines.append(f"处理人：{assignees}")
    lines.append(f"更新：{_format_time(item.updated_at)}")
    lines.append(f"链接：{item.url}")
    return "\n".join(lines)


def _single_line(value: str, limit: int) -> str:
    text = " ".join(value.replace("\r", " ").replace("\n", " ").split())
    return text if len(text) <= limit else text[: limit - 1] + "…"


def _format_time(value: datetime) -> str:
    local = value.astimezone()
    now = datetime.now().astimezone()
    pattern = "%m-%d %H:%M" if local.year == now.year else "%Y-%m-%d %H:%M"
    return local.strftime(pattern)
