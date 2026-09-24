"""GitHub webhook event types supported by the notifier."""

from enum import StrEnum

from githubkit_schemas.latest import webhooks


class GitHubWebhookEvent(StrEnum):
    """GitHub 官方 X-GitHub-Event 请求头中的事件名。"""

    PUSH = "push"
    PULL_REQUEST = "pull_request"
    ISSUES = "issues"
    ISSUE_COMMENT = "issue_comment"
    PULL_REQUEST_REVIEW = "pull_request_review"
    PULL_REQUEST_REVIEW_COMMENT = "pull_request_review_comment"
    WORKFLOW_RUN = "workflow_run"
    RELEASE = "release"
    DEPLOYMENT_STATUS = "deployment_status"
    DEPENDABOT_ALERT = "dependabot_alert"
    CODE_SCANNING_ALERT = "code_scanning_alert"
    SECRET_SCANNING_ALERT = "secret_scanning_alert"
    DISCUSSION = "discussion"
    DISCUSSION_COMMENT = "discussion_comment"
    ISSUE_DEPENDENCIES = "issue_dependencies"
    STAR = "star"


class GitHubWorkflowConclusion(StrEnum):
    """GitHub 官方 workflow_run.conclusion 字段中的结果值。"""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    SKIPPED = "skipped"
    NEUTRAL = "neutral"
    ACTION_REQUIRED = "action_required"
    STALE = "stale"


class DerivedEvent(StrEnum):
    """BioBot 自定义的过滤分类；这些值不是 GitHub 的事件名。"""

    PULL_REQUEST_MERGED = "pull_request.merged"
    WORKFLOW_SUCCESS = f"workflow_run.{GitHubWorkflowConclusion.SUCCESS}"
    WORKFLOW_FAILURE = f"workflow_run.{GitHubWorkflowConclusion.FAILURE}"
    WORKFLOW_CANCELLED = f"workflow_run.{GitHubWorkflowConclusion.CANCELLED}"
    WORKFLOW_TIMED_OUT = f"workflow_run.{GitHubWorkflowConclusion.TIMED_OUT}"
    WORKFLOW_SKIPPED = f"workflow_run.{GitHubWorkflowConclusion.SKIPPED}"
    WORKFLOW_NEUTRAL = f"workflow_run.{GitHubWorkflowConclusion.NEUTRAL}"
    WORKFLOW_ACTION_REQUIRED = f"workflow_run.{GitHubWorkflowConclusion.ACTION_REQUIRED}"
    WORKFLOW_STALE = f"workflow_run.{GitHubWorkflowConclusion.STALE}"


SUPPORTED_WEBHOOK_EVENTS = frozenset(GitHubWebhookEvent)


# action 名称来自 githubkit 的 GitHub Webhook schema；配置也允许只写事件名，
# 表示该事件下所有动作。PR 合并与工作流结果另外使用 BioBot 自定义分类。
def _actions(kind: GitHubWebhookEvent) -> tuple[str, ...]:
    schema = getattr(webhooks, f"{kind}_action_types", None)
    return tuple(schema) if isinstance(schema, dict) else ()


SUPPORTED_FILTER_KEYS = frozenset(
    {str(kind) for kind in GitHubWebhookEvent}
    | {f"{kind}.{action}" for kind in GitHubWebhookEvent for action in _actions(kind)}
    | {str(kind) for kind in DerivedEvent}
)
