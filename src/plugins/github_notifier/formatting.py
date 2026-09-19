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
    return _text(getattr(sender, "login", None)) or "GitHub 用户"


def _name(value: Any, fallback: str = "") -> str:
    """从 GitHub 的用户、标签等嵌套对象中读取一个适合展示的名字。"""
    if value is None:
        return fallback
    return (
        _text(getattr(value, "login", None))
        or _text(getattr(value, "name", None))
        or _text(getattr(value, "slug", None))
        or fallback
    )


def _label(event: Any) -> str:
    """读取标签名；不是标签事件时返回空字符串。"""
    return _name(getattr(event, "label", None))


def _assignee(event: Any) -> str:
    """读取被分配的用户；取消分配时 GitHub 可能不提供该字段。"""
    return _name(getattr(event, "assignee", None), "某位协作者")


ISSUE_ACTIONS = {
    "opened": "新建了",
    "closed": "关闭了",
    "reopened": "重新打开了",
    "edited": "编辑了",
    "deleted": "删除了",
    "transferred": "转移了",
    "pinned": "置顶了",
    "unpinned": "取消置顶了",
    "locked": "锁定了",
    "unlocked": "解锁了",
    "assigned": "给",
    "unassigned": "取消了",
    "labeled": "给",
    "unlabeled": "从",
    "milestoned": "给",
    "demilestoned": "取消了",
    "typed": "给",
    "untyped": "取消了",
    "field_added": "给",
    "field_removed": "从",
}


PULL_REQUEST_ACTIONS = {
    "opened": "新建了",
    "closed": "关闭了",
    "reopened": "重新打开了",
    "edited": "编辑了",
    "synchronize": "更新了",
    "converted_to_draft": "将",
    "ready_for_review": "将",
    "locked": "锁定了",
    "unlocked": "解锁了",
    "assigned": "给",
    "unassigned": "取消了",
    "labeled": "给",
    "unlabeled": "从",
    "milestoned": "给",
    "demilestoned": "取消了",
    "review_requested": "请求评审",
    "review_request_removed": "取消了",
    "auto_merge_enabled": "为",
    "auto_merge_disabled": "为",
    "enqueued": "将",
    "dequeued": "将",
    "stacked": "将",
}


def _item_action(action: str, actions: dict[str, str]) -> str:
    """把 GitHub 的英文 action 转成可直接放入句子的中文短语。"""
    return actions.get(action, "更新了")


def _item_line(
    actor: str, repository: str, kind: str, number: Any, action: str, *, extra: str = ""
) -> str:
    """生成“谁在什么仓库做了什么”的事件首行。"""
    item_name = "Issue" if kind == "issue" else "PR"
    return (
        f"[GitHub] {actor} 在 {repository} 中"
        f"{_item_action(action, ISSUE_ACTIONS if kind == 'issue' else PULL_REQUEST_ACTIONS)} "
        f"{item_name} #{_text(number)}{extra}"
    )


def _item_extra(event: Any, action: str) -> str:
    """补充标签、处理人等动作的宾语，让首行读起来完整。"""
    label = _label(event)
    milestone = _name(getattr(event, "milestone", None))
    assignee = _name(getattr(event, "assignee", None), "某位协作者")
    if action == "assigned":
        return f" 分配了处理人 {assignee}"
    if action == "unassigned":
        return " 的处理人"
    if action == "labeled":
        return f" 添加了标签 {label}" if label else " 添加了标签"
    if action == "unlabeled":
        return f" 移除了标签 {label}" if label else " 移除了标签"
    if action == "milestoned":
        return f" 关联了里程碑 {milestone}" if milestone else " 关联了里程碑"
    if action == "demilestoned":
        return f" 的里程碑 {milestone}" if milestone else " 的里程碑"
    if action == "typed":
        return " 设置了类型"
    if action == "untyped":
        return " 的类型"
    if action == "field_added":
        return " 添加了字段"
    if action == "field_removed":
        return " 移除了字段"
    if action == "converted_to_draft":
        return " 转为了草稿"
    if action == "ready_for_review":
        return " 标记为可以评审"
    if action == "review_request_removed":
        return " 的评审请求"
    if action == "auto_merge_enabled":
        return " 启用了自动合并"
    if action == "auto_merge_disabled":
        return " 停用了自动合并"
    if action == "enqueued":
        return " 加入了合并队列"
    if action == "dequeued":
        return " 移出了合并队列"
    if action == "stacked":
        return " 加入了堆叠队列"
    return ""


def _with_url(lines: list[str], url: Any) -> str:
    """在消息末尾追加详情链接，并统一限制链接长度。"""
    if url:
        lines.append(f"地址：{_text(url, 500)}")
    return "\n".join(lines)


def format_push(event: PushEvent) -> str:
    """格式化 push 事件。提交列表最多展示五条。"""
    name = _text(event.repository.full_name)
    ref = _text(event.ref)
    commits = event.commits
    actor = _actor(event)
    if ref.startswith("refs/tags/"):
        branch = ref.removeprefix("refs/tags/")
        ref_kind = "标签"
    else:
        branch = ref.removeprefix("refs/heads/")
        ref_kind = "分支"
    lines = [
        f"[GitHub] {actor} 向 {name} 的 {branch} {ref_kind}推送了 {len(commits)} 个提交"
    ]
    # Push 可能包含大量提交，只保留前五条并在末尾给出总数提示。
    for commit in commits[:5]:
        lines.append(f"- {_text(commit.id, 7)} {_text(commit.message)}")
    if len(commits) > 5:
        lines.append(f"……另有 {len(commits) - 5} 个提交")
    return _with_url(lines, event.compare or event.repository.html_url)


def format_pull_request(event: PullRequestEvent) -> str:
    """格式化 pull_request 事件。"""
    name = _text(event.repository.full_name)
    action = _text(event.action)
    item = event.pull_request
    # GitHub 的 closed + merged 组合比单独显示 closed 更有信息量。
    if action == "closed" and item.merged:
        action = "merged"
    if action == "merged":
        lines = [
            f"[GitHub] {_actor(event)} 在 {name} 中合并了 PR #{_text(item.number)}"
        ]
    else:
        lines = [
            _item_line(
                _actor(event),
                name,
                "pull_request",
                item.number,
                action,
                extra=_item_extra(event, action),
            )
        ]
    title = _text(item.title)
    if title:
        lines.append(f"标题：{title}")
    label = _label(event)
    if label and action not in {"labeled", "unlabeled"}:
        lines.append(f"标签：{label}")
    return _with_url(lines, item.html_url)


def format_issue(event: IssuesEvent) -> str:
    """格式化 issues 事件。"""
    name = _text(event.repository.full_name)
    item = event.issue
    action = _text(event.action)
    lines = [
        _item_line(
            _actor(event),
            name,
            "issue",
            item.number,
            action,
            extra=_item_extra(event, action),
        )
    ]
    title = _text(item.title)
    if title:
        lines.append(f"标题：{title}")
    label = _label(event)
    if label and action not in {"labeled", "unlabeled"}:
        lines.append(f"标签：{label}")
    return _with_url(lines, item.html_url)


def format_event(kind: str, event: WebhookEvent) -> str | None:
    """按 webhook 类型分发到对应 formatter；未支持的事件返回 ``None``。"""
    if kind == "push":
        return format_push(cast("PushEvent", event))
    if kind == "pull_request":
        return format_pull_request(cast("PullRequestEvent", event))
    if kind == "issues":
        return format_issue(cast("IssuesEvent", event))
    return None
