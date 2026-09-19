"""GitHub webhook event types supported by the notifier."""

from __future__ import annotations

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

SUPPORTED_WEBHOOK_EVENTS_TEXT = "、".join(SUPPORTED_WEBHOOK_EVENTS)
