"""轮询、事件标准化和 QQ 投递服务。

每个仓库只请求一次数据源，生成的事件再按订阅过滤并扇出到多个目标。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from githubkit.exception import RateLimitExceeded
from nonebot import get_bots, logger
from nonebot_plugin_orm import get_session
from sqlalchemy import func, or_, select

from .api import GitHubAPI, Json
from .config import plugin_config
from .events import branch_matches, event_matches
from .models import (
    GitHubDelivery,
    GitHubEvent,
    GitHubPollCursor,
    GitHubRepository,
    GitHubResourceSnapshot,
    GitHubSubscription,
    GitHubSubscriptionBranch,
    GitHubSubscriptionFilter,
)

if TYPE_CHECKING:
    from nonebot_plugin_orm import AsyncSession


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_time(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def aware(value: datetime | None) -> datetime | None:
    if value is not None and value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def json_hash(value: Any) -> str:
    raw = json.dumps(value, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()


def actor_login(value: Json) -> str | None:
    actor = value.get("actor") or value.get("user") or value.get("author")
    return actor.get("login") if isinstance(actor, dict) else None


@dataclass(slots=True)
class DetectedEvent:
    """轮询阶段产出的与平台无关事件对象。"""

    name: str
    key: str
    resource_type: str
    resource_id: str
    title: str
    html_url: str
    occurred_at: datetime
    actor: str | None
    payload: Json


class PollingService:
    """协调仓库轮询、事务落库、去重和消息投递。"""

    def __init__(self, api: GitHubAPI | None = None) -> None:
        self.api = api or GitHubAPI()
        self.lock = asyncio.Lock()

    async def poll_all(self, repository_id: int | None = None) -> None:
        """串行轮询启用订阅的仓库，并在完成后投递待发送事件。"""
        if self.lock.locked():
            logger.info("GitHub 轮询任务仍在运行，跳过本轮")
            return
        async with self.lock:
            async with get_session() as session:
                statement = (
                    select(GitHubRepository)
                    .join(
                        GitHubSubscription,
                        GitHubSubscription.repository_id == GitHubRepository.id,
                    )
                    .where(GitHubSubscription.enabled.is_(True))
                    .distinct()
                )
                if repository_id is not None:
                    statement = statement.where(GitHubRepository.id == repository_id)
                repositories = list((await session.scalars(statement)).all())

            # 一个仓库只轮询一次，避免多个 QQ 目标重复请求 GitHub。
            for repository in repositories:
                try:
                    await self._poll_repository(repository.id)
                except RateLimitExceeded as exc:
                    logger.warning(
                        "GitHub API 达到速率限制，将按服务端要求暂停：{}", repr(exc)
                    )
                    break
                except Exception:
                    logger.exception("轮询 GitHub 仓库 {} 失败", repository.full_name)
            await self.dispatch_pending()

    async def _poll_repository(self, repository_id: int) -> None:
        async with get_session() as session:
            repository = await session.get(GitHubRepository, repository_id)
            if repository is None:
                return
            subscriptions = await self._subscription_data(session, repository_id)
            patterns = set().union(*(value[0] for value in subscriptions.values()))
            owner, repo = repository.full_name.split("/", 1)

        metadata = await self.api.get_repository(owner, repo)
        async with get_session() as session:
            repository = await session.get(GitHubRepository, repository_id)
            if repository is None:
                return
            repository.full_name = metadata["full_name"]
            repository.html_url = metadata["html_url"]
            repository.default_branch = metadata.get("default_branch") or "main"
            repository.is_private = bool(metadata.get("private"))
            repository.archived = bool(metadata.get("archived"))
            repository.metadata_updated_at = parse_time(metadata.get("updated_at"))
            repository.updated_at = now_utc()
            await session.commit()

        # 只有确实存在对应订阅时才启用数据源，减少 API 请求和限流压力。
        sources: list[tuple[str, Any]] = []
        if any(name.startswith(("commit.", "branch.", "tag.")) for name in patterns):
            sources.append(("refs", self._poll_refs_and_commits))
        if any(name.startswith("commit.comment.") for name in patterns):
            sources.append(("commit_comments", self._poll_commit_comments))
        if any(name.startswith(("issue.", "pr.")) for name in patterns):
            sources.append(("issues", self._poll_issues))
            sources.append(("issue_events", self._poll_issue_events))
        if any(name.startswith(("issue.comment.", "pr.comment.")) for name in patterns):
            sources.append(("issue_comments", self._poll_issue_comments))
        if any(name.startswith("pr.review_comment.") for name in patterns):
            sources.append(("review_comments", self._poll_review_comments))
        if any(name.startswith("release.") for name in patterns):
            sources.append(("releases", self._poll_releases))
        if any(name.startswith("action.") for name in patterns):
            sources.append(("workflow_runs", self._poll_workflows))

        # 每个数据源独立提交游标；单个端点失败不会回滚其他已成功端点。
        for source, callback in sources:
            try:
                async with get_session() as session:
                    repository = await session.get(GitHubRepository, repository_id)
                    if repository is None:
                        return
                    cursor = await self._cursor(session, repository_id, source)
                    retry_at = aware(cursor.next_retry_at)
                    if retry_at and retry_at > now_utc():
                        continue
                    cursor.last_attempt_at = now_utc()
                    events = await callback(session, repository, cursor, subscriptions)
                    for event in events:
                        await self._record_event(
                            session, repository, subscriptions, event
                        )
                    # 首次成功只建立基线；各数据源内部会抑制历史事件。
                    cursor.initialized = True
                    cursor.last_success_at = now_utc()
                    cursor.failure_count = 0
                    cursor.next_retry_at = None
                    cursor.last_error = None
                    await session.commit()
            except RateLimitExceeded:
                await self._mark_failed(
                    repository_id, source, "GitHub API rate limited"
                )
                raise
            except Exception as exc:
                await self._mark_failed(repository_id, source, self._safe_error(exc))
                logger.exception(
                    "轮询 {} 的 {} 数据源失败", metadata["full_name"], source
                )

    async def _mark_failed(self, repository_id: int, source: str, error: str) -> None:
        async with get_session() as session:
            cursor = await self._cursor(session, repository_id, source)
            cursor.last_attempt_at = now_utc()
            cursor.failure_count += 1
            cursor.last_error = error[:1000]
            cursor.next_retry_at = now_utc() + timedelta(
                seconds=min(3600, 30 * 2 ** min(cursor.failure_count, 7))
            )
            await session.commit()

    @staticmethod
    def _safe_error(exc: Exception) -> str:
        text = f"{type(exc).__name__}: {exc}"
        token = plugin_config.github_poller_github_token
        return text.replace(token, "***") if token else text

    async def _subscription_data(
        self, session: AsyncSession, repository_id: int
    ) -> dict[int, tuple[set[str], set[str], GitHubSubscription]]:
        subscriptions = list(
            (
                await session.scalars(
                    select(GitHubSubscription).where(
                        GitHubSubscription.repository_id == repository_id,
                        GitHubSubscription.enabled.is_(True),
                    )
                )
            ).all()
        )
        result: dict[int, tuple[set[str], set[str], GitHubSubscription]] = {}
        for subscription in subscriptions:
            filters = set(
                await session.scalars(
                    select(GitHubSubscriptionFilter.event_pattern).where(
                        GitHubSubscriptionFilter.subscription_id == subscription.id
                    )
                )
            )
            branches = set(
                await session.scalars(
                    select(GitHubSubscriptionBranch.pattern).where(
                        GitHubSubscriptionBranch.subscription_id == subscription.id
                    )
                )
            )
            result[subscription.id] = (filters, branches, subscription)
        return result

    async def _cursor(
        self, session: AsyncSession, repository_id: int, source: str, scope: str = ""
    ) -> GitHubPollCursor:
        cursor = await session.scalar(
            select(GitHubPollCursor).where(
                GitHubPollCursor.repository_id == repository_id,
                GitHubPollCursor.source == source,
                GitHubPollCursor.scope == scope,
            )
        )
        if cursor is None:
            cursor = GitHubPollCursor(
                repository_id=repository_id,
                source=source,
                scope=scope,
                initialized=False,
                failure_count=0,
            )
            session.add(cursor)
            await session.flush()
        return cursor

    async def _snapshot(
        self,
        session: AsyncSession,
        repository_id: int,
        resource_type: str,
        external_id: str,
        state: Json,
        updated_at: datetime | None = None,
    ) -> Json | None:
        snapshot = await session.scalar(
            select(GitHubResourceSnapshot).where(
                GitHubResourceSnapshot.repository_id == repository_id,
                GitHubResourceSnapshot.resource_type == resource_type,
                GitHubResourceSnapshot.external_id == external_id,
            )
        )
        previous = snapshot.state_json if snapshot else None
        if snapshot is None:
            snapshot = GitHubResourceSnapshot(
                repository_id=repository_id,
                resource_type=resource_type,
                external_id=external_id,
                state_hash=json_hash(state),
                state_json=state,
                github_updated_at=updated_at,
                last_seen_at=now_utc(),
            )
            session.add(snapshot)
        else:
            snapshot.state_hash = json_hash(state)
            snapshot.state_json = state
            snapshot.github_updated_at = updated_at
            snapshot.last_seen_at = now_utc()
        return previous

    async def _poll_refs_and_commits(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        subscriptions: dict[int, tuple[set[str], set[str], GitHubSubscription]],
    ) -> list[DetectedEvent]:
        """比较分支、标签和提交快照，生成引用及提交事件。"""
        owner, repo = repository.full_name.split("/", 1)
        branches = await self.api.branches(owner, repo)
        tags = await self.api.tags(owner, repo)
        events: list[DetectedEvent] = []
        current_branches = {item["name"]: item["commit"]["sha"] for item in branches}
        current_tags = {item["name"]: item["commit"]["sha"] for item in tags}
        previous = cursor.state_json or {"branches": {}, "tags": {}}
        if cursor.initialized:
            for kind, old, current in (
                ("branch", previous.get("branches", {}), current_branches),
                ("tag", previous.get("tags", {}), current_tags),
            ):
                for name in current.keys() - old.keys():
                    events.append(
                        self._ref_event(
                            repository, kind, "created", name, current[name]
                        )
                    )
                for name in old.keys() - current.keys():
                    events.append(
                        self._ref_event(repository, kind, "deleted", name, old[name])
                    )
        cursor.state_json = {"branches": current_branches, "tags": current_tags}

        requested: set[str] = set()
        for patterns, branch_patterns, _subscription in subscriptions.values():
            if "commit.created" not in patterns:
                continue
            for pattern in branch_patterns or {"@default"}:
                if pattern == "@default":
                    requested.add(repository.default_branch)
                else:
                    requested.update(
                        name
                        for name in current_branches
                        if branch_matches({pattern}, name, repository.default_branch)
                    )
        for branch in sorted(requested):
            branch_cursor = await self._cursor(
                session, repository.id, "commits", branch
            )
            since = aware(branch_cursor.watermark_time)
            if since:
                since -= timedelta(seconds=2)
            commits = await self.api.commits(owner, repo, branch, since)
            for commit in reversed(commits):
                sha = commit["sha"]
                state = {"sha": sha}
                previous_commit = await self._snapshot(
                    session,
                    repository.id,
                    "commit",
                    sha,
                    state,
                    parse_time(
                        commit.get("commit", {}).get("committer", {}).get("date")
                    ),
                )
                if branch_cursor.initialized and previous_commit is None:
                    data = commit.get("commit", {})
                    event_time = (
                        parse_time(data.get("committer", {}).get("date")) or now_utc()
                    )
                    events.append(
                        DetectedEvent(
                            name="commit.created",
                            key=f"commit:{repository.github_id}:{branch}:{sha}",
                            resource_type="commit",
                            resource_id=sha,
                            title=(data.get("message") or sha).splitlines()[0],
                            html_url=commit.get("html_url") or repository.html_url,
                            occurred_at=event_time,
                            actor=actor_login(commit)
                            or data.get("author", {}).get("name"),
                            payload={"branch": branch, "sha": sha},
                        )
                    )
            branch_cursor.initialized = True
            branch_cursor.last_success_at = now_utc()
            branch_cursor.watermark_time = now_utc()
        return events

    @staticmethod
    def _ref_event(
        repository: GitHubRepository, kind: str, action: str, name: str, sha: str
    ) -> DetectedEvent:
        return DetectedEvent(
            name=f"{kind}.{action}",
            key=f"ref:{repository.github_id}:{kind}:{name}:{action}:{sha}",
            resource_type=kind,
            resource_id=name,
            title=f"{name} ({sha[:7]})",
            html_url=f"{repository.html_url}/tree/{name}",
            occurred_at=now_utc(),
            actor=None,
            payload={"name": name, "sha": sha},
        )

    async def _poll_commit_comments(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        _subscriptions: Any,
    ) -> list[DetectedEvent]:
        """按评论更新时间增量检查提交评论。"""
        owner, repo = repository.full_name.split("/", 1)
        items = await self.api.commit_comments(owner, repo)
        events: list[DetectedEvent] = []
        for item in reversed(items):
            state = {"body": item.get("body"), "updated_at": item.get("updated_at")}
            previous = await self._snapshot(
                session,
                repository.id,
                "commit_comment",
                str(item["id"]),
                state,
                parse_time(item.get("updated_at")),
            )
            if cursor.initialized and (previous is None or previous != state):
                action = "created" if previous is None else "updated"
                events.append(
                    self._comment_event(
                        repository, item, f"commit.comment.{action}", "commit_comment"
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    async def _poll_issues(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        subscriptions: dict[int, tuple[set[str], set[str], GitHubSubscription]],
    ) -> list[DetectedEvent]:
        """检查 Issue/PR 状态，并为变化的 PR 补查评审。"""
        owner, repo = repository.full_name.split("/", 1)
        pr_subscribed = any(
            pattern.startswith("pr.")
            for filters, _branches, _subscription in subscriptions.values()
            for pattern in filters
        )
        review_subscribed = any(
            pattern.startswith("pr.review.")
            for filters, _branches, _subscription in subscriptions.values()
            for pattern in filters
        )
        previous_poll = aware(cursor.watermark_time)
        since = previous_poll
        if since:
            since -= timedelta(seconds=2)
        items = await self.api.issues(owner, repo, since)
        events: list[DetectedEvent] = []
        for item in items:
            is_pr = "pull_request" in item
            if is_pr and not pr_subscribed:
                continue
            detail = (
                await self.api.pull(owner, repo, int(item["number"])) if is_pr else item
            )
            kind = "pr" if is_pr else "issue"
            state = self._issue_state(detail)
            previous = await self._snapshot(
                session,
                repository.id,
                kind,
                str(item["number"]),
                state,
                parse_time(item.get("updated_at")),
            )
            if cursor.initialized:
                events.extend(
                    self._issue_diff(
                        repository, detail, kind, previous, state, previous_poll
                    )
                )
            if is_pr and review_subscribed:
                events.extend(
                    await self._poll_reviews_for_pull(
                        session, repository, detail, cursor.initialized
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    @staticmethod
    def _issue_state(item: Json) -> Json:
        return {
            "title": item.get("title"),
            "body": item.get("body"),
            "state": item.get("state"),
            "locked": bool(item.get("locked")),
            "labels": sorted(label.get("name") for label in item.get("labels", [])),
            "assignees": sorted(
                user.get("login") for user in item.get("assignees", [])
            ),
            "milestone": (item.get("milestone") or {}).get("title"),
            "draft": bool(item.get("draft")),
            "head": (item.get("head") or {}).get("sha"),
            "merged_at": item.get("merged_at"),
            "updated_at": item.get("updated_at"),
        }

    def _issue_diff(
        self,
        repository: GitHubRepository,
        item: Json,
        kind: str,
        previous: Json | None,
        state: Json,
        previous_poll: datetime | None,
    ) -> list[DetectedEvent]:
        number = str(item["number"])
        base = {
            "resource_type": kind,
            "resource_id": number,
            "title": f"#{number} {item.get('title', '')}",
            "html_url": item.get("html_url") or repository.html_url,
            "actor": actor_login(item),
            "payload": {"number": item["number"]},
        }
        actions: list[str] = []
        created_at = parse_time(item.get("created_at"))
        if previous is None and (
            previous_poll is None
            or (created_at is not None and created_at >= previous_poll)
        ):
            actions.append("opened")
        elif previous is not None:
            if previous.get("title") != state.get("title") or previous.get(
                "body"
            ) != state.get("body"):
                actions.append("edited")
            if (
                kind == "pr"
                and previous.get("head")
                and previous.get("head") != state.get("head")
            ):
                actions.append("head_updated")
        occurred = parse_time(item.get("updated_at")) or now_utc()
        return [
            DetectedEvent(
                name=f"{kind}.{action}",
                key=f"resource:{repository.github_id}:{kind}:{number}:{action}:{item.get('updated_at')}",
                occurred_at=occurred,
                **base,
            )
            for action in dict.fromkeys(actions)
        ]

    async def _poll_reviews_for_pull(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        pull: Json,
        initialized: bool,
    ) -> list[DetectedEvent]:
        owner, repo = repository.full_name.split("/", 1)
        reviews = await self.api.pull_reviews(owner, repo, int(pull["number"]))
        events: list[DetectedEvent] = []
        for review in reviews:
            state = {
                "state": review.get("state"),
                "body": review.get("body"),
                "submitted_at": review.get("submitted_at"),
            }
            previous = await self._snapshot(
                session,
                repository.id,
                "pr_review",
                str(review["id"]),
                state,
                parse_time(review.get("submitted_at")),
            )
            if initialized and previous is None:
                events.append(self._review_event(repository, pull, review, "submitted"))
        return events

    @staticmethod
    def _review_event(
        repository: GitHubRepository, pull: Json, review: Json, action: str
    ) -> DetectedEvent:
        return DetectedEvent(
            name=f"pr.review.{action}",
            key=f"review:{repository.github_id}:{review['id']}:{action}:{review.get('submitted_at')}",
            resource_type="pr_review",
            resource_id=str(review["id"]),
            title=f"#{pull['number']} {pull.get('title', '')}",
            html_url=review.get("html_url")
            or pull.get("html_url")
            or repository.html_url,
            occurred_at=parse_time(review.get("submitted_at")) or now_utc(),
            actor=actor_login(review),
            payload={"number": pull["number"], "state": review.get("state")},
        )

    async def _poll_issue_events(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        subscriptions: dict[int, tuple[set[str], set[str], GitHubSubscription]],
    ) -> list[DetectedEvent]:
        """把 GitHub Issue Events 映射为 Issue 或 PR 的标准动作。"""
        owner, repo = repository.full_name.split("/", 1)
        pr_subscribed = any(
            pattern.startswith("pr.")
            for filters, _branches, _subscription in subscriptions.values()
            for pattern in filters
        )
        items = await self.api.issue_events(owner, repo)
        mapping = {
            "closed": "closed",
            "reopened": "reopened",
            "assigned": "assigned",
            "unassigned": "unassigned",
            "labeled": "labeled",
            "unlabeled": "unlabeled",
            "milestoned": "milestoned",
            "demilestoned": "demilestoned",
            "locked": "locked",
            "unlocked": "unlocked",
            "transferred": "transferred",
            "merged": "merged",
            "ready_for_review": "ready_for_review",
            "converted_to_draft": "converted_to_draft",
            "review_requested": "review_requested",
            "review_request_removed": "review_request_removed",
            "review_dismissed": "review.dismissed",
        }
        events: list[DetectedEvent] = []
        for item in reversed(items):
            external_id = str(item["id"])
            previous = await self._snapshot(
                session,
                repository.id,
                "issue_event",
                external_id,
                {"event": item.get("event")},
                parse_time(item.get("created_at")),
            )
            if (
                not cursor.initialized
                or previous is not None
                or item.get("event") not in mapping
            ):
                continue
            issue = item.get("issue") or {}
            kind = "pr" if "pull_request" in issue else "issue"
            if kind == "pr" and not pr_subscribed:
                continue
            action = mapping[item["event"]]
            if action in {
                "merged",
                "ready_for_review",
                "converted_to_draft",
                "review_requested",
                "review_request_removed",
                "review.dismissed",
            }:
                kind = "pr"
            name = f"{kind}.{action}"
            events.append(
                DetectedEvent(
                    name=name,
                    key=f"issue-event:{repository.github_id}:{external_id}",
                    resource_type=f"{kind}_event",
                    resource_id=external_id,
                    title=f"#{issue.get('number', '')} {issue.get('title', '')}",
                    html_url=issue.get("html_url") or repository.html_url,
                    occurred_at=parse_time(item.get("created_at")) or now_utc(),
                    actor=actor_login(item),
                    payload={"number": issue.get("number"), "event": item.get("event")},
                )
            )
        cursor.watermark_time = now_utc()
        return events

    async def _poll_issue_comments(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        _subscriptions: Any,
    ) -> list[DetectedEvent]:
        """轮询仓库级 Issue 评论，并依据资源快照区分 Issue 与 PR。"""
        owner, repo = repository.full_name.split("/", 1)
        since = aware(cursor.watermark_time)
        if since:
            since -= timedelta(seconds=2)
        items = await self.api.issue_comments(owner, repo, since)
        events: list[DetectedEvent] = []
        for item in items:
            number = item.get("issue_url", "").rstrip("/").split("/")[-1]
            is_pr = bool(
                await session.scalar(
                    select(GitHubResourceSnapshot.id).where(
                        GitHubResourceSnapshot.repository_id == repository.id,
                        GitHubResourceSnapshot.resource_type == "pr",
                        GitHubResourceSnapshot.external_id == number,
                    )
                )
            )
            kind = "pr" if is_pr else "issue"
            state = {"body": item.get("body"), "updated_at": item.get("updated_at")}
            previous = await self._snapshot(
                session,
                repository.id,
                f"{kind}_comment",
                str(item["id"]),
                state,
                parse_time(item.get("updated_at")),
            )
            if cursor.initialized and (previous is None or previous != state):
                action = "created" if previous is None else "updated"
                events.append(
                    self._comment_event(
                        repository,
                        item,
                        f"{kind}.comment.{action}",
                        f"{kind}_comment",
                        number,
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    async def _poll_review_comments(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        _subscriptions: Any,
    ) -> list[DetectedEvent]:
        """轮询 PR Review Comment 的创建和编辑。"""
        owner, repo = repository.full_name.split("/", 1)
        since = aware(cursor.watermark_time)
        if since:
            since -= timedelta(seconds=2)
        items = await self.api.review_comments(owner, repo, since)
        events: list[DetectedEvent] = []
        for item in items:
            state = {"body": item.get("body"), "updated_at": item.get("updated_at")}
            previous = await self._snapshot(
                session,
                repository.id,
                "pr_review_comment",
                str(item["id"]),
                state,
                parse_time(item.get("updated_at")),
            )
            if cursor.initialized and (previous is None or previous != state):
                action = "created" if previous is None else "updated"
                number = item.get("pull_request_url", "").rstrip("/").split("/")[-1]
                events.append(
                    self._comment_event(
                        repository,
                        item,
                        f"pr.review_comment.{action}",
                        "pr_review_comment",
                        number,
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    @staticmethod
    def _comment_event(
        repository: GitHubRepository,
        item: Json,
        name: str,
        resource_type: str,
        number: str = "",
    ) -> DetectedEvent:
        body = (item.get("body") or "").replace("\n", " ").strip()
        prefix = f"#{number} " if number else ""
        return DetectedEvent(
            name=name,
            key=f"comment:{repository.github_id}:{resource_type}:{item['id']}:{name}:{item.get('updated_at')}",
            resource_type=resource_type,
            resource_id=str(item["id"]),
            title=f"{prefix}{body[:120] or '评论'}",
            html_url=item.get("html_url") or repository.html_url,
            occurred_at=parse_time(item.get("updated_at") or item.get("created_at"))
            or now_utc(),
            actor=actor_login(item),
            payload={"number": number, "commit_id": item.get("commit_id")},
        )

    async def _poll_releases(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        _subscriptions: Any,
    ) -> list[DetectedEvent]:
        """比较 Release 快照，识别发布、预发布和内容更新。"""
        owner, repo = repository.full_name.split("/", 1)
        items = await self.api.releases(owner, repo)
        events: list[DetectedEvent] = []
        for item in reversed(items):
            state = {
                "name": item.get("name"),
                "body": item.get("body"),
                "draft": item.get("draft"),
                "prerelease": item.get("prerelease"),
                "published_at": item.get("published_at"),
                "updated_at": item.get("updated_at"),
            }
            previous = await self._snapshot(
                session,
                repository.id,
                "release",
                str(item["id"]),
                state,
                parse_time(item.get("updated_at")),
            )
            if not cursor.initialized or item.get("draft"):
                continue
            action = None
            if previous is None:
                action = "prereleased" if item.get("prerelease") else "published"
            elif previous != state:
                action = "updated"
            if action:
                events.append(
                    DetectedEvent(
                        name=f"release.{action}",
                        key=f"release:{repository.github_id}:{item['id']}:{action}:{item.get('updated_at')}",
                        resource_type="release",
                        resource_id=str(item["id"]),
                        title=item.get("name") or item.get("tag_name") or "Release",
                        html_url=item.get("html_url") or repository.html_url,
                        occurred_at=parse_time(
                            item.get("published_at") or item.get("updated_at")
                        )
                        or now_utc(),
                        actor=actor_login(item),
                        payload={
                            "tag": item.get("tag_name"),
                            "prerelease": bool(item.get("prerelease")),
                        },
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    async def _poll_workflows(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        cursor: GitHubPollCursor,
        _subscriptions: Any,
    ) -> list[DetectedEvent]:
        """比较 Workflow Run 状态；快速运行只报告最终可观察结果。"""
        owner, repo = repository.full_name.split("/", 1)
        items = await self.api.workflow_runs(owner, repo)
        events: list[DetectedEvent] = []
        for item in reversed(items):
            attempt = item.get("run_attempt") or 1
            external_id = f"{item['id']}:{attempt}"
            state = {
                "status": item.get("status"),
                "conclusion": item.get("conclusion"),
                "updated_at": item.get("updated_at"),
            }
            previous = await self._snapshot(
                session,
                repository.id,
                "workflow_run",
                external_id,
                state,
                parse_time(item.get("updated_at")),
            )
            if not cursor.initialized or previous == state:
                continue
            action = None
            if item.get("status") == "completed":
                conclusion = item.get("conclusion") or "neutral"
                action = (
                    "succeeded"
                    if conclusion == "success"
                    else "failed"
                    if conclusion == "failure"
                    else conclusion
                )
            elif previous is None or previous.get("status") != item.get("status"):
                action = "started"
            if action and f"action.{action}" in {
                f"action.{x}"
                for x in (
                    "started",
                    "succeeded",
                    "failed",
                    "cancelled",
                    "timed_out",
                    "action_required",
                    "neutral",
                    "skipped",
                    "stale",
                )
            }:
                events.append(
                    DetectedEvent(
                        name=f"action.{action}",
                        key=f"workflow:{repository.github_id}:{external_id}:{action}:{item.get('updated_at')}",
                        resource_type="workflow_run",
                        resource_id=external_id,
                        title=item.get("name")
                        or item.get("display_title")
                        or "GitHub Actions",
                        html_url=item.get("html_url") or repository.html_url,
                        occurred_at=parse_time(
                            item.get("updated_at") or item.get("created_at")
                        )
                        or now_utc(),
                        actor=actor_login(item),
                        payload={
                            "branch": item.get("head_branch"),
                            "event": item.get("event"),
                            "conclusion": item.get("conclusion"),
                        },
                    )
                )
        cursor.watermark_time = now_utc()
        return events

    async def _record_event(
        self,
        session: AsyncSession,
        repository: GitHubRepository,
        subscriptions: dict[int, tuple[set[str], set[str], GitHubSubscription]],
        event: DetectedEvent,
    ) -> None:
        """在同一事务中完成事件幂等落库和匹配订阅的投递任务创建。"""
        if event.name not in {
            name
            for filters, _branches, _sub in subscriptions.values()
            for name in filters
        }:
            return
        existing = await session.scalar(
            select(GitHubEvent.id).where(GitHubEvent.event_key == event.key)
        )
        if existing:
            return
        category, action = event.name.rsplit(".", 1)
        record = GitHubEvent(
            repository_id=repository.id,
            event_key=event.key,
            category=category,
            action=action,
            resource_type=event.resource_type,
            resource_id=event.resource_id,
            actor_login=event.actor,
            title=event.title,
            html_url=event.html_url,
            occurred_at=event.occurred_at,
            payload_json={**event.payload, "event_name": event.name},
            created_at=now_utc(),
        )
        session.add(record)
        await session.flush()
        for subscription_id, (filters, branches, subscription) in subscriptions.items():
            if not event_matches(filters, event.name):
                continue
            subscribed_at = aware(subscription.updated_at)
            if subscribed_at and event.occurred_at < subscribed_at:
                continue
            branch = event.payload.get("branch") or (
                event.payload.get("name") if event.name.startswith("branch.") else None
            )
            if (
                (event.name == "commit.created" or event.name.startswith("branch."))
                and branch
                and not branch_matches(
                    branches or {"@default"}, branch, repository.default_branch
                )
            ):
                continue
            session.add(
                GitHubDelivery(
                    event_id=record.id,
                    subscription_id=subscription_id,
                    status="pending",
                    attempt_count=0,
                )
            )

    async def dispatch_pending(self) -> None:
        """合并待投递事件并发送；失败任务保留以便后续退避重试。"""
        async with get_session() as session:
            rows = (
                await session.execute(
                    select(
                        GitHubDelivery,
                        GitHubEvent,
                        GitHubSubscription,
                        GitHubRepository,
                    )
                    .join(GitHubEvent, GitHubEvent.id == GitHubDelivery.event_id)
                    .join(
                        GitHubSubscription,
                        GitHubSubscription.id == GitHubDelivery.subscription_id,
                    )
                    .join(
                        GitHubRepository,
                        GitHubRepository.id == GitHubEvent.repository_id,
                    )
                    .where(
                        GitHubDelivery.status.in_(("pending", "failed")),
                        GitHubDelivery.attempt_count
                        < plugin_config.github_poller_delivery_max_attempts,
                        or_(
                            GitHubDelivery.next_attempt_at.is_(None),
                            GitHubDelivery.next_attempt_at <= now_utc(),
                        ),
                        GitHubSubscription.enabled.is_(True),
                    )
                    .order_by(GitHubEvent.occurred_at)
                )
            ).all()
            grouped: dict[tuple[int, int, str], list[Any]] = defaultdict(list)
            for delivery, event, subscription, repository in rows:
                grouped[(subscription.id, repository.id, event.category)].append(
                    (delivery, event, subscription, repository)
                )

            for group in grouped.values():
                delivery, _event, subscription, repository = group[0]
                selected = group[: plugin_config.github_poller_max_events_per_message]
                lines = [f"[GitHub] {repository.full_name} · {selected[0][1].category}"]
                for _delivery, event, _subscription, _repository in selected:
                    actor = f" · {event.actor_login}" if event.actor_login else ""
                    lines.append(
                        f"- {event.action}: {event.title}{actor}\n  {event.html_url}"
                    )
                omitted = len(group) - len(selected)
                if omitted:
                    lines.append(
                        f"另有 {omitted} 条更新未在本条展开\n{repository.html_url}"
                    )
                text = "\n".join(lines)
                if len(text) > plugin_config.github_poller_max_message_length:
                    text = (
                        text[: plugin_config.github_poller_max_message_length - 40]
                        + f"…\n{repository.html_url}"
                    )
                error = await self._send(subscription, text)
                for item, *_rest in selected:
                    item.attempt_count += 1
                    if error is None:
                        item.status = "sent"
                        item.sent_at = now_utc()
                        item.last_error = None
                        item.next_attempt_at = None
                    else:
                        item.status = "failed"
                        item.last_error = error[:1000]
                        item.next_attempt_at = now_utc() + timedelta(
                            seconds=min(3600, 30 * 2 ** min(item.attempt_count, 7))
                        )
                await session.commit()

    async def _send(self, subscription: GitHubSubscription, message: str) -> str | None:
        errors: list[str] = []
        for bot in get_bots().values():
            try:
                if subscription.target_type == "group":
                    await bot.send_group_msg(
                        group_id=int(subscription.target_id), message=message
                    )
                else:
                    await bot.send_private_msg(
                        user_id=int(subscription.target_id), message=message
                    )
                return None
            except Exception as exc:
                errors.append(self._safe_error(exc))
        return "; ".join(errors) if errors else "没有可用的 OneBot V11 实例"

    async def counts(self) -> tuple[int, int, datetime | None, int]:
        async with get_session() as session:
            repositories = (
                await session.scalar(select(func.count(GitHubRepository.id))) or 0
            )
            subscriptions = (
                await session.scalar(select(func.count(GitHubSubscription.id))) or 0
            )
            last_success = await session.scalar(
                select(func.max(GitHubPollCursor.last_success_at))
            )
            failures = (
                await session.scalar(select(func.sum(GitHubPollCursor.failure_count)))
                or 0
            )
            return repositories, subscriptions, aware(last_success), failures


service = PollingService()
