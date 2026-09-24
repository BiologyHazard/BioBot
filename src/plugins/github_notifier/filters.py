"""从配置文件选择哪些 GitHub Webhook 事件需要通知。"""

import re
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import plugin_config
from .events import (
    DerivedEvent,
    GitHubWebhookEvent,
    SUPPORTED_FILTER_KEYS,
)

REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9-]+/[A-Za-z0-9_.-]+\Z")
DEFAULT_CONFIG = Path(__file__).with_name("default_filters.toml")


@dataclass(frozen=True)
class EventFilters:
    """有效默认规则及每仓库的完整覆盖规则。"""

    default_events: frozenset[str]
    repositories: dict[str, frozenset[str]]

    def events_for(self, repository: str) -> frozenset[str]:
        return self.repositories.get(repository.lower(), self.default_events)

    def webhook_events(self, repository: str) -> tuple[str, ...]:
        """GitHub 设置页应勾选的原始 Webhook 事件类型。"""
        return tuple(
            sorted({key.partition(".")[0] for key in self.events_for(repository)})
        )

    def allows(self, repository: str, kind: str, event: Any) -> bool:
        """过滤已验签、已解析的事件；PR 合并和 CI 结果单独分类。"""
        selected = self.events_for(repository)
        if kind in selected:
            return True

        action = getattr(event, "action", None)
        if kind == GitHubWebhookEvent.PULL_REQUEST and action == "closed":
            if event.pull_request.merged:
                return DerivedEvent.PULL_REQUEST_MERGED in selected
            return "pull_request.closed" in selected

        if action and f"{kind}.{action}" in selected:
            return True
        if kind == GitHubWebhookEvent.WORKFLOW_RUN and action == "completed":
            conclusion = getattr(event.workflow_run, "conclusion", None)
            return f"workflow_run.{conclusion}" in selected
        return False


def _read_config(path: Path) -> dict[str, Any]:
    with path.open("rb") as file:
        data = tomllib.load(file)
    unknown = set(data) - {"default", "repositories"}
    if unknown:
        raise ValueError(f"{path}: 未知配置项 {', '.join(sorted(unknown))}")
    return data


def _events(value: Any, source: str) -> frozenset[str]:
    if not isinstance(value, dict) or set(value) != {"events"}:
        raise ValueError(f"{source}: 需要 events 数组")
    items = value["events"]
    if not isinstance(items, list) or not all(isinstance(item, str) for item in items):
        raise ValueError(f"{source}: events 必须是字符串数组")
    if not items:
        raise ValueError(f"{source}: events 至少需要一个事件")
    unknown = set(items) - SUPPORTED_FILTER_KEYS
    if unknown:
        raise ValueError(f"{source}: 未知事件分类 {', '.join(sorted(unknown))}")
    return frozenset(items)


def load_filters(override_path: Path | None = None) -> EventFilters:
    """读取版本化默认配置，再用可选文件覆盖默认和指定仓库。"""
    bundled = _read_config(DEFAULT_CONFIG)
    default = _events(bundled.get("default"), str(DEFAULT_CONFIG))
    repositories: dict[str, frozenset[str]] = {}
    if override_path is not None:
        config = _read_config(override_path)
        if "default" in config:
            default = _events(config["default"], f"{override_path}: default")
        configured_repositories = config.get("repositories", {})
        if not isinstance(configured_repositories, dict):
            raise ValueError(f"{override_path}: repositories 必须是表")
        for name, rules in configured_repositories.items():
            if not REPOSITORY_PATTERN.fullmatch(name):
                raise ValueError(f"{override_path}: 无效仓库名 {name}")
            normalized = name.lower()
            if normalized in repositories:
                raise ValueError(f"{override_path}: 重复仓库名 {name}")
            repositories[normalized] = _events(rules, f"{override_path}: {name}")
    return EventFilters(default, repositories)


event_filters = load_filters(plugin_config.github_notifier_filter_config)
