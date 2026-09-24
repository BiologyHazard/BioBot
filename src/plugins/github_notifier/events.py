"""GitHub webhook event types supported by the notifier."""

from __future__ import annotations

from typing import TYPE_CHECKING, cast

if TYPE_CHECKING:
    from githubkit_schemas.latest.webhooks import (
        DiscussionEvent,
        IssuesEvent,
        PullRequestEvent,
        PushEvent,
        WebhookEvent,
        WorkflowRunEvent,
    )

# 可解析并格式化的事件类型，包括暂不推送的类型。
SUPPORTED_WEBHOOK_EVENTS: tuple[str, ...] = (
    "push",
    "pull_request",
    "issues",
    "issue_comment",
    "pull_request_review",
    "pull_request_review_comment",
    "workflow_run",
    "release",
    "deployment_status",
    "dependabot_alert",
    "code_scanning_alert",
    "secret_scanning_alert",
    "discussion",
    "discussion_comment",
    "issue_dependencies",
)

# 当前允许进入通知队列的事件类型。
NOTIFICATION_WEBHOOK_EVENTS: tuple[str, ...] = (
    "push",
    "pull_request",
    "issues",
    "workflow_run",
    "release",
    "deployment_status",
    "dependabot_alert",
    "code_scanning_alert",
    "secret_scanning_alert",
    "discussion",
)
NOTIFICATION_WEBHOOK_EVENTS_TEXT = "、".join(NOTIFICATION_WEBHOOK_EVENTS)
NOTIFIED_ITEM_ACTIONS = frozenset({"opened", "closed", "reopened"})
NOTIFIED_DISCUSSION_ACTIONS = frozenset({"created", "closed", "reopened"})


def should_notify(kind: str, event: WebhookEvent) -> bool:
    """判断已解析的 webhook 事件是否需要发送通知。"""
    if kind not in NOTIFICATION_WEBHOOK_EVENTS:
        return False
    if kind == "push":
        push = cast("PushEvent", event)
        return not push.deleted and bool(push.commits)
    if kind == "issues":
        return cast("IssuesEvent", event).action in NOTIFIED_ITEM_ACTIONS
    if kind == "pull_request":
        return cast("PullRequestEvent", event).action in NOTIFIED_ITEM_ACTIONS
    if kind == "discussion":
        return cast("DiscussionEvent", event).action in NOTIFIED_DISCUSSION_ACTIONS
    if kind == "workflow_run":
        workflow = cast("WorkflowRunEvent", event)
        return (
            workflow.action == "completed"
            and workflow.workflow_run.conclusion != "success"
        )
    return True
