import unittest

import nonebot

nonebot.init()

from src.plugins.github_query.query import GitHubQuery


class FakeResponse:
    def __init__(self, body: object) -> None:
        self.body = body

    def json(self) -> object:
        return self.body


class FakeIssues:
    async def async_list_for_repo(self, owner: str, repo: str, **kwargs: object):
        return FakeResponse(
            [
                {
                    "number": 8,
                    "title": "This is a pull request",
                    "html_url": "https://github.com/example/project/pull/8",
                    "pull_request": {},
                    "labels": [],
                    "user": {"login": "octocat"},
                    "assignees": [],
                    "updated_at": "2026-09-25T06:00:00Z",
                },
                {
                    "number": 7,
                    "title": "Visible issue",
                    "html_url": "https://github.com/example/project/issues/7",
                    "labels": [{"name": "bug"}, {"name": "backend"}],
                    "user": {"login": "alice"},
                    "assignees": [{"login": "bob"}],
                    "updated_at": "2026-09-25T05:00:00Z",
                },
            ]
        )


class FakeRepositories:
    async def async_get(self, owner: str, repo: str):
        return FakeResponse(
            {
                "full_name": "Example/Project",
                "private": True,
            }
        )


class FakePulls:
    def __init__(self) -> None:
        self.kwargs: dict[str, object] = {}

    async def async_list(self, owner: str, repo: str, **kwargs: object):
        self.kwargs = kwargs
        return FakeResponse(
            [
                {
                    "number": 12,
                    "title": "Draft pull request",
                    "html_url": "https://github.com/example/project/pull/12",
                    "labels": [{"name": "enhancement"}],
                    "user": {"login": "alice"},
                    "assignees": [],
                    "updated_at": "2026-09-25T07:00:00Z",
                    "draft": True,
                },
                {
                    "number": 11,
                    "title": "Older pull request",
                    "html_url": "https://github.com/example/project/pull/11",
                    "labels": [],
                    "user": {"login": "bob"},
                    "assignees": [],
                    "updated_at": "2026-09-24T07:00:00Z",
                    "draft": False,
                },
            ]
        )


class FakeRest:
    def __init__(self) -> None:
        self.issues = FakeIssues()
        self.repos = FakeRepositories()
        self.pulls = FakePulls()


class FakeGitHub:
    def __init__(self) -> None:
        self.rest = FakeRest()


class GitHubQueryTests(unittest.IsolatedAsyncioTestCase):
    async def test_repository_reports_canonical_name_and_visibility(self) -> None:
        query = GitHubQuery(FakeGitHub())

        repository = await query.repository("example", "project")

        self.assertEqual(repository.full_name, "Example/Project")
        self.assertTrue(repository.private)

    async def test_open_pull_requests_honor_limit_and_include_draft_state(self) -> None:
        client = FakeGitHub()
        query = GitHubQuery(client)

        items = await query.open_pull_requests("example", "project", limit=1)

        self.assertEqual([item.number for item in items], [12])
        self.assertTrue(items[0].draft)
        self.assertEqual(client.rest.pulls.kwargs["state"], "open")
        self.assertEqual(client.rest.pulls.kwargs["sort"], "updated")
        self.assertEqual(client.rest.pulls.kwargs["direction"], "desc")

    async def test_open_issues_exclude_pull_requests(self) -> None:
        query = GitHubQuery(FakeGitHub())

        items = await query.open_issues("example", "project", limit=10)

        self.assertEqual([item.number for item in items], [7])
        self.assertEqual(items[0].labels, ("bug", "backend"))
        self.assertEqual(items[0].author, "alice")
        self.assertEqual(items[0].assignees, ("bob",))


if __name__ == "__main__":
    unittest.main()
