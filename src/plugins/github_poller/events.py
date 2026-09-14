"""命令参数和订阅事件的纯函数定义。

这里不访问数据库或 GitHub，便于命令层和轮询层复用同一套匹配规则。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from fnmatch import fnmatchcase
from shlex import split as shlex_split

EVENTS: dict[str, tuple[str, ...]] = {
    # 键是可用于命令的类别；值是该类别允许的原子动作。
    "commit": ("created",),
    "commit.comment": ("created", "updated"),
    "branch": ("created", "deleted"),
    "tag": ("created", "deleted"),
    "issue": (
        "opened",
        "edited",
        "reopened",
        "closed",
        "assigned",
        "unassigned",
        "labeled",
        "unlabeled",
        "milestoned",
        "demilestoned",
        "locked",
        "unlocked",
        "transferred",
    ),
    "issue.comment": ("created", "updated"),
    "pr": (
        "opened",
        "edited",
        "reopened",
        "closed",
        "merged",
        "ready_for_review",
        "converted_to_draft",
        "head_updated",
        "assigned",
        "unassigned",
        "labeled",
        "unlabeled",
        "milestoned",
        "demilestoned",
        "review_requested",
        "review_request_removed",
    ),
    "pr.review": ("submitted", "dismissed"),
    "pr.comment": ("created", "updated"),
    "pr.review_comment": ("created", "updated"),
    "release": ("published", "prereleased", "updated"),
    "action": (
        "started",
        "succeeded",
        "failed",
        "cancelled",
        "timed_out",
        "action_required",
        "neutral",
        "skipped",
        "stale",
    ),
}

ALL_EVENTS = frozenset(
    f"{category}.{action}" for category, actions in EVENTS.items() for action in actions
)
DEFAULT_EVENTS = frozenset(
    {
        "commit.created",
        "issue.opened",
        "issue.reopened",
        "issue.closed",
        "pr.opened",
        "pr.reopened",
        "pr.closed",
        "pr.merged",
        "release.published",
        "release.prereleased",
        "action.failed",
        "action.cancelled",
        "action.timed_out",
        "action.action_required",
    }
)


def expand_event_patterns(patterns: list[str]) -> set[str]:
    """把 default、all、类别名和原子事件统一展开为原子事件集合。"""
    if not patterns or patterns == ["default"]:
        return set(DEFAULT_EVENTS)
    result: set[str] = set()
    for pattern in patterns:
        pattern = pattern.lower()
        if pattern == "all":
            result.update(ALL_EVENTS)
        elif pattern == "default":
            result.update(DEFAULT_EVENTS)
        elif children := {
            event for event in ALL_EVENTS if event.startswith(f"{pattern}.")
        }:
            result.update(children)
        elif pattern in ALL_EVENTS:
            result.add(pattern)
        else:
            raise ValueError(f"不支持的事件：{pattern}")
    return result


def event_matches(patterns: set[str], event_name: str) -> bool:
    """判断一个标准化事件是否被订阅过滤器命中。"""
    return event_name in patterns


def branch_matches(patterns: set[str], branch: str, default_branch: str) -> bool:
    """匹配分支通配符；@default 始终解析为仓库当前默认分支。"""
    return any(
        branch == default_branch
        if pattern == "@default"
        else fnmatchcase(branch, pattern)
        for pattern in patterns
    )


@dataclass(slots=True)
class Target:
    type: str
    id: str


@dataclass(slots=True)
class ParsedArgs:
    positional: list[str] = field(default_factory=list)
    groups: list[str] = field(default_factory=list)
    privates: list[str] = field(default_factory=list)
    branches: list[str] = field(default_factory=list)


def parse_args(text: str) -> ParsedArgs:
    """解析 ghp 子命令参数，保留重复目标和分支选项。"""
    result = ParsedArgs()
    tokens = shlex_split(text)
    index = 0
    options = {
        "--group": result.groups,
        "--private": result.privates,
        "--branch": result.branches,
    }
    while index < len(tokens):
        token = tokens[index]
        if token in options:
            index += 1
            if index >= len(tokens) or tokens[index].startswith("--"):
                raise ValueError(f"{token} 缺少参数")
            value = tokens[index]
            if token != "--branch" and not value.isdigit():
                raise ValueError(f"{token} 必须是数字 ID")
            options[token].append(value)
        elif token.startswith("--"):
            raise ValueError(f"未知选项：{token}")
        else:
            result.positional.append(token)
        index += 1
    return result


def normalize_repository(value: str) -> tuple[str, str]:
    """将 owner/repo、GitHub URL 或 .git 地址规范化为 API 参数。"""
    value = value.strip().rstrip("/")
    for prefix in ("https://github.com/", "http://github.com/", "github.com/"):
        if value.lower().startswith(prefix):
            value = value[len(prefix) :]
            break
    if value.endswith(".git"):
        value = value[:-4]
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("仓库格式应为 owner/repo 或标准 GitHub 仓库 URL")
    return parts[0], parts[1]
