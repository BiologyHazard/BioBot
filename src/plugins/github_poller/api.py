"""GitHubKit REST API 的薄封装。

缓存头由 GitHubKit 负责；本模块只负责分页、限流状态和响应 JSON 转换。
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from githubkit import GitHub
from githubkit.exception import RateLimitExceeded
from nonebot import logger

from .config import plugin_config

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

Json = dict[str, Any]


@dataclass(slots=True)
class RateState:
    """当前 API 配额和暂停窗口，仅保存在进程内，不写入数据库。"""

    limit: int | None = None
    remaining: int | None = None
    reset_at: datetime | None = None
    paused_until: datetime | None = None


class GitHubAPI:
    """按资源端点提供轮询所需的最小 GitHub REST API。"""

    def __init__(self) -> None:
        self.client = GitHub(
            auth=plugin_config.github_poller_github_token,
            user_agent=plugin_config.github_poller_user_agent,
            timeout=plugin_config.github_poller_request_timeout,
            http_cache=True,
            auto_retry=False,
        )
        self.rate = RateState()

    @property
    def authenticated(self) -> bool:
        return bool(plugin_config.github_poller_github_token)

    async def _call(self, call: Awaitable[Any], description: str) -> Any:
        # 限流窗口内不再发起请求，避免重试风暴进一步消耗配额。
        now = datetime.now(UTC)
        if self.rate.paused_until and self.rate.paused_until > now:
            raise RuntimeError(
                f"GitHub API 已暂停至 {self.rate.paused_until.astimezone().isoformat()}"
            )
        logger.debug("GitHub Poller 请求：{}", description)
        try:
            response = await call
        except RateLimitExceeded as exc:
            self.rate.paused_until = now + exc.retry_after
            self._update_rate(exc.response.headers)
            raise
        self._update_rate(response.headers)
        logger.debug(
            "GitHub Poller 响应：{}（剩余配额：{}）",
            description,
            self.rate.remaining if self.rate.remaining is not None else "未知",
        )
        return response

    def _update_rate(self, headers: Any) -> None:
        try:
            if value := headers.get("x-ratelimit-limit"):
                self.rate.limit = int(value)
            if value := headers.get("x-ratelimit-remaining"):
                self.rate.remaining = int(value)
            if value := headers.get("x-ratelimit-reset"):
                self.rate.reset_at = datetime.fromtimestamp(int(value), UTC)
            retry_after = headers.get("retry-after")
            if retry_after:
                self.rate.paused_until = datetime.now(UTC) + timedelta(
                    seconds=int(retry_after)
                )
            elif self.rate.remaining == 0 and self.rate.reset_at:
                self.rate.paused_until = self.rate.reset_at
        except (TypeError, ValueError):
            return

    async def _pages(
        self,
        method: Callable[..., Awaitable[Any]],
        /,
        *args: Any,
        item_key: str | None = None,
        description: str,
        **kwargs: Any,
    ) -> list[Json]:
        """读取分页端点；达到最大页数或返回短页时停止。"""
        result: list[Json] = []
        per_page = plugin_config.github_poller_per_page
        for page in range(1, plugin_config.github_poller_max_pages + 1):
            response = await self._call(
                method(*args, per_page=per_page, page=page, **kwargs),
                f"GET {description} page={page}",
            )
            body = response.json()
            items = body.get(item_key, []) if item_key else body
            result.extend(items)
            if len(items) < per_page:
                break
        return result

    async def get_repository(self, owner: str, repo: str) -> Json:
        response = await self._call(
            self.client.rest.repos.async_get(owner, repo),
            f"GET /repos/{owner}/{repo}",
        )
        return response.json()

    async def commits(
        self, owner: str, repo: str, branch: str, since: datetime | None
    ) -> list[Json]:
        kwargs: dict[str, Any] = {"sha": branch}
        if since:
            kwargs["since"] = since
        return await self._pages(
            self.client.rest.repos.async_list_commits,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/commits branch={branch}",
            **kwargs,
        )

    async def branches(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.repos.async_list_branches,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/branches",
        )

    async def tags(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.repos.async_list_tags,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/tags",
        )

    async def commit_comments(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.repos.async_list_commit_comments_for_repo,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/comments",
        )

    async def issues(self, owner: str, repo: str, since: datetime | None) -> list[Json]:
        kwargs: dict[str, Any] = {"state": "all", "sort": "updated", "direction": "asc"}
        if since:
            kwargs["since"] = since
        return await self._pages(
            self.client.rest.issues.async_list_for_repo,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/issues",
            **kwargs,
        )

    async def issue_events(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.issues.async_list_events_for_repo,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/issues/events",
        )

    async def issue_comments(
        self, owner: str, repo: str, since: datetime | None
    ) -> list[Json]:
        kwargs: dict[str, Any] = {"sort": "updated", "direction": "asc"}
        if since:
            kwargs["since"] = since
        return await self._pages(
            self.client.rest.issues.async_list_comments_for_repo,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/issues/comments",
            **kwargs,
        )

    async def pull(self, owner: str, repo: str, number: int) -> Json:
        response = await self._call(
            self.client.rest.pulls.async_get(owner, repo, number),
            f"GET /repos/{owner}/{repo}/pulls/{number}",
        )
        return response.json()

    async def pull_reviews(self, owner: str, repo: str, number: int) -> list[Json]:
        return await self._pages(
            self.client.rest.pulls.async_list_reviews,
            owner,
            repo,
            number,
            description=f"/repos/{owner}/{repo}/pulls/{number}/reviews",
        )

    async def review_comments(
        self, owner: str, repo: str, since: datetime | None
    ) -> list[Json]:
        kwargs: dict[str, Any] = {"sort": "updated", "direction": "asc"}
        if since:
            kwargs["since"] = since
        return await self._pages(
            self.client.rest.pulls.async_list_review_comments_for_repo,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/pulls/comments",
            **kwargs,
        )

    async def releases(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.repos.async_list_releases,
            owner,
            repo,
            description=f"/repos/{owner}/{repo}/releases",
        )

    async def workflow_runs(self, owner: str, repo: str) -> list[Json]:
        return await self._pages(
            self.client.rest.actions.async_list_workflow_runs_for_repo,
            owner,
            repo,
            item_key="workflow_runs",
            description=f"/repos/{owner}/{repo}/actions/runs",
        )

    async def rate_limit(self) -> Json:
        response = await self._call(
            self.client.rest.rate_limit.async_get(),
            "GET /rate_limit",
        )
        return response.json()
