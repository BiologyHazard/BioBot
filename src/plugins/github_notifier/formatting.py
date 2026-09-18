"""Plain-text summaries for the typed GitHub webhook events."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from typing import Any

    from githubkit_schemas.latest.webhooks import (
        IssuesEvent,
        PullRequestEvent,
        PushEvent,
        WebhookEvent,
    )


class WebhookRepositoryEnvelope(BaseModel):
    """The only payload fields needed before the repository secret is known."""

    full_name: str


class WebhookEnvelope(BaseModel):
    """从 webhook payload 中提取仓库名的最小结构。"""

    repository: WebhookRepositoryEnvelope


def _text(value: Any, limit: int = 200) -> str:
    """将事件字段转成单行、有限长度的通知文本。"""
    return str(value or "").replace("\r", " ").replace("\n", " ")[:limit]


def _actor(event: WebhookEvent) -> str:
    """读取事件发送者的 GitHub 登录名。"""
    sender = getattr(event, "sender", None)
    return _text(getattr(sender, "login", None))


def format_event(kind: str, event: WebhookEvent) -> str | None:
    """将支持的 GitHub 事件转换为 QQ 纯文本消息。

    未支持的事件返回 ``None``。提交列表最多展示五条，避免一次 webhook
    产生过长的 QQ 消息。
    """
    if kind == "push":
        push = cast("PushEvent", event)
        name = _text(push.repository.full_name)
        ref = _text(push.ref)
        commits = push.commits
        lines = [f"[GitHub] {name} 推送", f"分支：{ref.removeprefix('refs/heads/')}"]
        actor = _actor(push)
        if actor:
            lines.append(f"操作者：{actor}")
        # Push 可能包含大量提交，只保留前五条并在末尾给出总数提示。
        for commit in commits[:5]:
            lines.append(f"- {_text(commit.id, 7)} {_text(commit.message)}")
        if len(commits) > 5:
            lines.append(f"……另有 {len(commits) - 5} 个提交")
        url = push.compare or push.repository.html_url

    elif kind == "pull_request":
        pull_request = cast("PullRequestEvent", event)
        name = _text(pull_request.repository.full_name)
        action = _text(pull_request.action)
        item = pull_request.pull_request
        # GitHub 的 closed + merged 组合比单独显示 closed 更有信息量。
        if action == "closed" and item.merged:
            action = "merged"
        lines = [
            f"[GitHub] {name} PR #{_text(item.number)} {action}",
            f"标题：{_text(item.title)}",
        ]
        actor = _actor(pull_request)
        if actor:
            lines.append(f"操作者：{actor}")
        url = item.html_url

    elif kind == "issues":
        issues = cast("IssuesEvent", event)
        name = _text(issues.repository.full_name)
        item = issues.issue
        lines = [
            f"[GitHub] {name} Issue #{_text(item.number)} {_text(issues.action)}",
            f"标题：{_text(item.title)}",
        ]
        actor = _actor(issues)
        if actor:
            lines.append(f"操作者：{actor}")
        url = item.html_url

    else:
        return None

    if url:
        lines.append(f"地址：{_text(url, 500)}")
    return "\n".join(lines)
