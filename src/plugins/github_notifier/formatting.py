"""Plain-text summaries for the typed GitHub webhook events."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

from pydantic import BaseModel

if TYPE_CHECKING:
    from typing import Any

    from githubkit_schemas.latest.webhooks import (
        CodeScanningAlertEvent,
        DependabotAlertEvent,
        DeploymentStatusEvent,
        DiscussionCommentEvent,
        DiscussionEvent,
        IssueCommentEvent,
        IssueDependenciesEvent,
        IssuesEvent,
        PullRequestEvent,
        PullRequestReviewCommentEvent,
        PullRequestReviewEvent,
        PushEvent,
        ReleaseEvent,
        SecretScanningAlertEvent,
        WebhookEvent,
        WorkflowRunEvent,
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
        or _text(getattr(value, "title", None))
        or _text(getattr(value, "slug", None))
        or fallback
    )


def _path(value: Any, *attributes: str, limit: int = 200) -> str:
    """读取嵌套 payload 字段，并安全转换为通知文本。"""
    current = value
    for attribute in attributes:
        current = getattr(current, attribute, None)
        if current is None:
            return ""
    return _text(current, limit)


def _number(value: Any, fallback: str = "") -> str:
    """读取 Issue、PR 或告警编号。"""
    return _text(getattr(value, "number", None)) or fallback


def _subject_line(item: Any, kind: str, number: str = "") -> str:
    """生成 Issue、PR 或 Discussion 的简短标识。"""
    item_number = number or _number(item)
    item_name = "Issue" if kind == "issue" else kind
    return f"{item_name} #{item_number}" if item_number else item_name


def _body_line(value: Any, label: str = "内容") -> str | None:
    """读取正文并限制长度；删除事件通常没有可展示正文。"""
    body = _text(getattr(value, "body", None), 500)
    return f"{label}：{body}" if body else None


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


COMMENT_ACTIONS = {
    "created": "发表了评论",
    "edited": "编辑了评论",
    "deleted": "删除了评论",
    "pinned": "置顶了评论",
    "unpinned": "取消置顶了评论",
}


REVIEW_ACTIONS = {
    "edited": "编辑了评审",
    "dismissed": "撤销了评审",
}


WORKFLOW_ACTIONS = {
    "requested": "已请求执行",
    "in_progress": "正在执行",
}


RELEASE_ACTIONS = {
    "created": "创建了",
    "edited": "编辑了",
    "deleted": "删除了",
    "prereleased": "发布了预发布版本",
    "published": "发布了",
    "released": "发布了正式版本",
    "unpublished": "取消发布了",
}


DEPLOYMENT_STATES = {
    "success": "成功",
    "failure": "失败",
    "error": "失败",
    "cancelled": "已取消",
    "inactive": "已失效",
    "pending": "等待中",
    "queued": "排队中",
    "in_progress": "进行中",
    "waiting": "等待审批",
    "neutral": "已完成",
}


DEPENDABOT_ACTIONS = {
    "created": "发现了漏洞",
    "fixed": "已修复",
    "dismissed": "已忽略",
    "reopened": "重新打开了",
    "reintroduced": "再次出现了",
    "auto_dismissed": "被自动忽略了",
    "auto_reopened": "被自动重新打开了",
    "assignees_changed": "更新了处理人",
}


CODE_SCANNING_ACTIONS = {
    "created": "发现了",
    "fixed": "已修复",
    "closed_by_user": "被用户关闭了",
    "reopened": "重新打开了",
    "reopened_by_user": "被用户重新打开了",
    "updated_assignment": "更新了处理人",
    "appeared_in_branch": "在其他分支再次出现了",
}


SECRET_SCANNING_ACTIONS = {
    "created": "发现了",
    "publicly_leaked": "检测到公开泄露",
    "resolved": "已解决",
    "reopened": "重新打开了",
    "assigned": "分配了处理人",
    "unassigned": "取消了处理人",
    "validated": "验证了",
    "metadata_created": "新增了元数据",
    "metadata_removed": "移除了元数据",
}


DISCUSSION_ACTIONS = {
    "created": "发起了",
    "edited": "编辑了",
    "deleted": "删除了",
    "answered": "将",
    "unanswered": "取消了",
    "closed": "关闭了",
    "reopened": "重新打开了",
    "locked": "锁定了",
    "unlocked": "解锁了",
    "pinned": "置顶了",
    "unpinned": "取消置顶了",
    "transferred": "转移了",
    "labeled": "给",
    "unlabeled": "从",
    "category_changed": "修改了",
}


DISCUSSION_COMMENT_ACTIONS = {
    "created": "发表了讨论评论",
    "edited": "编辑了讨论评论",
    "deleted": "删除了讨论评论",
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


def _discussion_extra(event: Any, action: str) -> str:
    """补充 Discussion 动作的标签、回答状态等宾语。"""
    label = _label(event)
    if action == "answered":
        return " 标记为已回答"
    if action == "unanswered":
        return " 的已回答状态"
    if action == "labeled":
        return f" 添加了标签 {label}" if label else " 添加了标签"
    if action == "unlabeled":
        return f" 移除了标签 {label}" if label else " 移除了标签"
    if action == "category_changed":
        return " 的讨论分类"
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
    if getattr(event, "deleted", False):
        lines = [f"[GitHub] {actor} 删除了 {name} 的 {branch} {ref_kind}"]
        return _with_url(lines, event.repository.html_url)
    if getattr(event, "created", False) and not commits:
        lines = [f"[GitHub] {actor} 创建了 {name} 的 {branch} {ref_kind}"]
        return _with_url(lines, event.repository.html_url)
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


def format_issue_comment(event: IssueCommentEvent) -> str:
    """格式化 Issue 或 PR 的普通评论事件。"""
    repository = _text(event.repository.full_name)
    issue = event.issue
    comment = event.comment
    item_kind = "PR" if getattr(issue, "pull_request", None) else "issue"
    subject = _subject_line(issue, item_kind)
    action = _text(event.action)
    phrase = COMMENT_ACTIONS.get(action, "更新了评论")
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 的 {subject} 下{phrase}"]
    title = _text(getattr(issue, "title", None))
    if title:
        lines.append(f"标题：{title}")
    body = _body_line(comment, "评论")
    if body:
        lines.append(body)
    return _with_url(
        lines,
        _path(comment, "html_url") or _path(issue, "html_url"),
    )


def format_pull_request_review(event: PullRequestReviewEvent) -> str:
    """格式化 PR 评审提交、编辑和撤销事件。"""
    repository = _text(event.repository.full_name)
    pull_request = event.pull_request
    review = event.review
    subject = _subject_line(pull_request, "PR")
    action = _text(event.action)
    if action == "submitted":
        state = _path(review, "state").lower()
        phrase = {
            "approved": "批准了",
            "changes_requested": "要求修改了",
            "commented": "评论了",
        }.get(state, "提交了评审")
    else:
        phrase = REVIEW_ACTIONS.get(action, "更新了评审")
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 中{phrase} {subject}"]
    title = _text(getattr(pull_request, "title", None))
    if title:
        lines.append(f"标题：{title}")
    body = _body_line(review, "评审意见")
    if body:
        lines.append(body)
    return _with_url(
        lines,
        _path(review, "html_url") or _path(pull_request, "html_url"),
    )


def format_pull_request_review_comment(
    event: PullRequestReviewCommentEvent,
) -> str:
    """格式化 PR 代码行评论事件。"""
    repository = _text(event.repository.full_name)
    pull_request = event.pull_request
    comment = event.comment
    subject = _subject_line(pull_request, "PR")
    action = _text(event.action)
    phrase = {
        "created": "发表了代码评论",
        "edited": "编辑了代码评论",
        "deleted": "删除了代码评论",
    }.get(action, "更新了代码评论")
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 的 {subject} 中{phrase}"]
    path = _path(comment, "path")
    line = _path(comment, "line") or _path(comment, "original_line")
    if path:
        lines.append(f"位置：{path}{f':{line}' if line else ''}")
    body = _body_line(comment, "评论")
    if body:
        lines.append(body)
    return _with_url(
        lines,
        _path(comment, "html_url") or _path(pull_request, "html_url"),
    )


def format_workflow_run(event: WorkflowRunEvent) -> str | None:
    """格式化 GitHub Actions 工作流运行事件。"""
    repository = _text(event.repository.full_name)
    workflow_run = event.workflow_run
    workflow_name = (
        _path(event.workflow, "name") or _path(workflow_run, "name") or "GitHub Actions"
    )
    action = _text(event.action)
    # 请求执行、开始执行和成功完成都是正常流程，不需要推送。
    if action in {"requested", "in_progress"}:
        return None
    if action == "completed":
        conclusion = _path(workflow_run, "conclusion").lower()
        if conclusion == "success":
            return None
        outcome = {
            "failure": "执行失败",
            "cancelled": "已取消",
            "skipped": "已跳过",
            "timed_out": "执行超时",
            "action_required": "需要人工处理",
            "neutral": "执行完成",
        }.get(conclusion, "执行完成")
    else:
        outcome = WORKFLOW_ACTIONS.get(action, "状态已更新")
    lines = [f"[GitHub] {repository} 的工作流「{workflow_name}」{outcome}"]
    branch = _path(workflow_run, "head_branch")
    if branch:
        lines.append(f"分支：{branch}")
    sha = _path(workflow_run, "head_sha", limit=7)
    if sha:
        lines.append(f"提交：{sha}")
    run_number = _path(workflow_run, "run_number")
    if run_number:
        lines.append(f"运行编号：#{run_number}")
    return _with_url(lines, _path(workflow_run, "html_url"))


def format_release(event: ReleaseEvent) -> str:
    """格式化 Release 事件。"""
    repository = _text(event.repository.full_name)
    release = event.release
    action = _text(event.action)
    phrase = RELEASE_ACTIONS.get(action, "更新了")
    if action == "created" and getattr(release, "draft", False):
        phrase = "保存了"
    release_name = _path(release, "name") or _path(release, "tag_name") or "未命名版本"
    lines = [
        f"[GitHub] {_actor(event)} 在 {repository} 中{phrase} Release {release_name}"
    ]
    body = _body_line(release, "发布说明")
    if body:
        lines.append(body)
    return _with_url(lines, _path(release, "html_url"))


def format_deployment_status(event: DeploymentStatusEvent) -> str:
    """格式化部署状态事件。"""
    repository = _text(event.repository.full_name)
    status = event.deployment_status
    deployment = event.deployment
    state = _path(status, "state").lower()
    state_text = DEPLOYMENT_STATES.get(state, state or "状态未知")
    environment = _path(status, "environment") or _path(deployment, "environment")
    target = f"{environment} 环境" if environment else "目标环境"
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 的 {target} 部署{state_text}"]
    ref = _path(deployment, "ref") or _path(deployment, "sha", limit=7)
    if ref:
        lines.append(f"版本：{ref}")
    description = _path(status, "description")
    if description:
        lines.append(f"说明：{description}")
    return _with_url(
        lines,
        _path(status, "target_url")
        or _path(status, "environment_url")
        or _path(deployment, "html_url"),
    )


def _format_security_alert(
    event: Any,
    category: str,
    actions: dict[str, str],
    subject: str,
    *,
    severity: str = "",
) -> str:
    """格式化三类安全告警的公共消息结构。"""
    repository = _text(event.repository.full_name)
    alert = event.alert
    action = _text(event.action)
    number = _number(alert)
    alert_label = f" #{number}" if number else ""
    phrase = actions.get(action, "状态已更新")
    lines = [f"[GitHub] {repository} 的 {category}{alert_label} {phrase}：{subject}"]
    if severity:
        lines.append(f"严重程度：{severity}")
    state = _path(alert, "state")
    if state:
        lines.append(f"状态：{state}")
    if action not in {"created", "fixed", "resolved", "reopened"}:
        lines.append(f"操作者：{_actor(event)}")
    return _with_url(lines, _path(alert, "html_url") or _path(alert, "url"))


def format_dependabot_alert(event: DependabotAlertEvent) -> str:
    """格式化 Dependabot 安全告警事件。"""
    alert = event.alert
    subject = (
        _path(alert, "security_advisory", "summary")
        or _path(alert, "dependency", "package", "name")
        or "依赖安全告警"
    )
    severity = _path(alert, "security_advisory", "severity")
    return _format_security_alert(
        event,
        "Dependabot 告警",
        DEPENDABOT_ACTIONS,
        subject,
        severity=severity,
    )


def format_code_scanning_alert(event: CodeScanningAlertEvent) -> str:
    """格式化代码扫描告警事件。"""
    alert = event.alert
    subject = (
        _path(alert, "rule", "description")
        or _path(alert, "rule", "name")
        or "代码扫描告警"
    )
    severity = _path(alert, "rule", "security_severity_level") or _path(
        alert, "rule", "severity"
    )
    return _format_security_alert(
        event,
        "代码扫描告警",
        CODE_SCANNING_ACTIONS,
        subject,
        severity=severity,
    )


def format_secret_scanning_alert(event: SecretScanningAlertEvent) -> str:
    """格式化秘密扫描告警事件。"""
    alert = event.alert
    subject = (
        _path(alert, "secret_type_display_name")
        or _path(alert, "secret_type")
        or "秘密泄露告警"
    )
    return _format_security_alert(
        event,
        "秘密扫描告警",
        SECRET_SCANNING_ACTIONS,
        subject,
    )


def format_discussion(event: DiscussionEvent) -> str:
    """格式化 GitHub Discussion 事件。"""
    repository = _text(event.repository.full_name)
    discussion = event.discussion
    action = _text(event.action)
    subject = _subject_line(discussion, "Discussion")
    phrase = DISCUSSION_ACTIONS.get(action, "更新了")
    lines = [
        f"[GitHub] {_actor(event)} 在 {repository} 中{phrase} "
        f"{subject}{_discussion_extra(event, action)}"
    ]
    title = _text(getattr(discussion, "title", None))
    if title:
        lines.append(f"标题：{title}")
    label = _label(event)
    if label and action not in {"labeled", "unlabeled"}:
        lines.append(f"标签：{label}")
    body = _body_line(discussion)
    if body and action in {"created", "edited"}:
        lines.append(body)
    return _with_url(lines, _path(discussion, "html_url"))


def format_discussion_comment(event: DiscussionCommentEvent) -> str:
    """格式化 Discussion 评论事件。"""
    repository = _text(event.repository.full_name)
    discussion = event.discussion
    comment = event.comment
    subject = _subject_line(discussion, "Discussion")
    action = _text(event.action)
    phrase = DISCUSSION_COMMENT_ACTIONS.get(action, "更新了讨论评论")
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 的 {subject} 下{phrase}"]
    title = _text(getattr(discussion, "title", None))
    if title:
        lines.append(f"标题：{title}")
    body = _body_line(comment, "评论")
    if body:
        lines.append(body)
    return _with_url(
        lines,
        _path(comment, "html_url") or _path(discussion, "html_url"),
    )


def format_issue_dependencies(event: IssueDependenciesEvent) -> str:
    """格式化 Issue 阻塞关系变化事件。"""
    repository = _text(event.repository.full_name)
    action = _text(event.action)
    blocked = getattr(event, "blocked_issue", None)
    blocking = getattr(event, "blocking_issue", None)
    if action.startswith("blocked_by_"):
        main_issue, related_issue = blocked, blocking
        relation = "被" if action.endswith("_added") else "不再被"
        phrase = f"Issue #{_number(main_issue)} {relation} Issue #{_number(related_issue)} 阻塞"
    else:
        main_issue, related_issue = blocking, blocked
        relation = "阻塞了" if action.endswith("_added") else "不再阻塞"
        phrase = (
            f"Issue #{_number(main_issue)} {relation} Issue #{_number(related_issue)}"
        )
    lines = [f"[GitHub] {_actor(event)} 在 {repository} 中{phrase}"]
    return _with_url(
        lines,
        _path(main_issue, "html_url") or _path(related_issue, "html_url"),
    )


def format_event(kind: str, event: WebhookEvent) -> str | None:
    """按 webhook 类型分发到对应 formatter；未支持的事件返回 ``None``。"""
    if kind == "push":
        return format_push(cast("PushEvent", event))
    if kind == "pull_request":
        return format_pull_request(cast("PullRequestEvent", event))
    if kind == "issues":
        return format_issue(cast("IssuesEvent", event))
    if kind == "issue_comment":
        return format_issue_comment(cast("IssueCommentEvent", event))
    if kind == "pull_request_review":
        return format_pull_request_review(cast("PullRequestReviewEvent", event))
    if kind == "pull_request_review_comment":
        return format_pull_request_review_comment(
            cast("PullRequestReviewCommentEvent", event)
        )
    if kind == "workflow_run":
        return format_workflow_run(cast("WorkflowRunEvent", event))
    if kind == "release":
        return format_release(cast("ReleaseEvent", event))
    if kind == "deployment_status":
        return format_deployment_status(cast("DeploymentStatusEvent", event))
    if kind == "dependabot_alert":
        return format_dependabot_alert(cast("DependabotAlertEvent", event))
    if kind == "code_scanning_alert":
        return format_code_scanning_alert(cast("CodeScanningAlertEvent", event))
    if kind == "secret_scanning_alert":
        return format_secret_scanning_alert(cast("SecretScanningAlertEvent", event))
    if kind == "discussion":
        return format_discussion(cast("DiscussionEvent", event))
    if kind == "discussion_comment":
        return format_discussion_comment(cast("DiscussionCommentEvent", event))
    if kind == "issue_dependencies":
        return format_issue_dependencies(cast("IssueDependenciesEvent", event))
    return None
