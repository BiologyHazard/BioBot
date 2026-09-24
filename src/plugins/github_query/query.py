"""Read-only GitHub queries with repository data normalized for presentation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any


@dataclass(frozen=True, slots=True)
class GitHubItem:
    number: int
    title: str
    url: str
    labels: tuple[str, ...]
    author: str | None
    assignees: tuple[str, ...]
    updated_at: datetime
    draft: bool = False


@dataclass(frozen=True, slots=True)
class GitHubRepository:
    full_name: str
    private: bool


class GitHubQuery:
    """Expose the read operations needed by the QQ command."""

    def __init__(self, client: Any, *, max_pages: int = 10) -> None:
        self.client = client
        self.max_pages = max_pages

    async def repository(self, owner: str, repo: str) -> GitHubRepository:
        response = await self.client.rest.repos.async_get(owner, repo)
        body = response.json()
        return GitHubRepository(
            full_name=body["full_name"],
            private=body["private"],
        )

    async def open_pull_requests(
        self, owner: str, repo: str, *, limit: int
    ) -> list[GitHubItem]:
        """Return recently updated open pull requests."""
        if limit < 1:
            raise ValueError("limit must be positive")

        result: list[GitHubItem] = []
        per_page = min(limit, 100)
        for page in range(1, self.max_pages + 1):
            response = await self.client.rest.pulls.async_list(
                owner,
                repo,
                state="open",
                sort="updated",
                direction="desc",
                per_page=per_page,
                page=page,
            )
            body = response.json()
            for item in body:
                result.append(_item_from_json(item, draft=bool(item.get("draft"))))
                if len(result) == limit:
                    return result
            if len(body) < per_page:
                break
        return result

    async def open_issues(
        self, owner: str, repo: str, *, limit: int
    ) -> list[GitHubItem]:
        """Return recently updated open issues, excluding pull requests."""
        if limit < 1:
            raise ValueError("limit must be positive")

        result: list[GitHubItem] = []
        per_page = 100
        for page in range(1, self.max_pages + 1):
            response = await self.client.rest.issues.async_list_for_repo(
                owner,
                repo,
                state="open",
                sort="updated",
                direction="desc",
                per_page=per_page,
                page=page,
            )
            body = response.json()
            for item in body:
                if "pull_request" in item:
                    continue
                result.append(_item_from_json(item))
                if len(result) == limit:
                    return result
            if len(body) < per_page:
                break
        return result


def _item_from_json(item: dict[str, Any], *, draft: bool = False) -> GitHubItem:
    user = item.get("user") or {}
    return GitHubItem(
        number=item["number"],
        title=item["title"],
        url=item["html_url"],
        labels=tuple(
            label["name"] for label in item.get("labels", []) if label.get("name")
        ),
        author=user.get("login"),
        assignees=tuple(
            assignee["login"]
            for assignee in item.get("assignees", [])
            if assignee.get("login")
        ),
        updated_at=datetime.fromisoformat(item["updated_at"]),
        draft=draft,
    )
