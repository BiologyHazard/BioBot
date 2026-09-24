import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

import nonebot

nonebot.init(github_notifier_webhook_payload_url="https://example.com/github/webhook")

from src.plugins.github_notifier.filters import load_filters  # noqa: E402
from src.plugins.github_notifier.formatting import format_event  # noqa: E402


def event(action: str, **fields: object) -> SimpleNamespace:
    return SimpleNamespace(action=action, **fields)


class EventFiltersTest(unittest.TestCase):
    def test_default_rules_include_requested_events_only(self) -> None:
        filters = load_filters()
        repository = "bio/project"

        for kind, payload in (
            ("issues", event("opened")),
            ("issues", event("closed")),
            ("issues", event("reopened")),
            ("pull_request", event("opened")),
            ("pull_request", event("reopened")),
            ("pull_request", event("closed", pull_request=event("", merged=False))),
            ("pull_request", event("closed", pull_request=event("", merged=True))),
            (
                "workflow_run",
                event("completed", workflow_run=event("", conclusion="failure")),
            ),
            ("star", event("created")),
            ("release", event("edited")),
        ):
            with self.subTest(kind=kind, action=payload.action):
                self.assertTrue(filters.allows(repository, kind, payload))

        for kind, payload in (
            ("push", event("")),
            ("issues", event("edited")),
            (
                "workflow_run",
                event("completed", workflow_run=event("", conclusion="success")),
            ),
            (
                "workflow_run",
                event("completed", workflow_run=event("", conclusion="cancelled")),
            ),
            (
                "workflow_run",
                event("in_progress", workflow_run=event("", conclusion="failure")),
            ),
            ("star", event("deleted")),
        ):
            with self.subTest(kind=kind, action=payload.action):
                self.assertFalse(filters.allows(repository, kind, payload))

    def test_repository_rule_replaces_default_and_distinguishes_merge(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "filters.toml"
            config.write_text(
                '[repositories."bio/project"]\n'
                'events = ["pull_request.closed", "star.created"]\n'
            )
            filters = load_filters(config)

        merged = event("closed", pull_request=event("", merged=True))
        unmerged = event("closed", pull_request=event("", merged=False))
        self.assertFalse(filters.allows("bio/project", "pull_request", merged))
        self.assertTrue(filters.allows("bio/project", "pull_request", unmerged))
        self.assertFalse(filters.allows("bio/project", "issues", event("opened")))
        self.assertTrue(filters.allows("other/repo", "issues", event("opened")))
        self.assertEqual(
            filters.webhook_events("bio/project"), ("pull_request", "star")
        )

    def test_invalid_event_name_fails_loading(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "filters.toml"
            config.write_text('[default]\nevents = ["issues.openned"]\n')
            with self.assertRaisesRegex(ValueError, "issues.openned"):
                load_filters(config)

    def test_global_default_can_be_replaced(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            config = Path(directory) / "filters.toml"
            config.write_text('[default]\nevents = ["release"]\n')
            filters = load_filters(config)

        self.assertFalse(filters.allows("bio/project", "issues", event("opened")))
        self.assertTrue(filters.allows("bio/project", "release", event("published")))

    def test_new_star_has_readable_notification(self) -> None:
        payload = event(
            "created",
            sender=SimpleNamespace(login="octocat"),
            repository=SimpleNamespace(
                full_name="bio/project", html_url="https://github.com/bio/project"
            ),
        )
        message = format_event("star", payload)
        self.assertIn("octocat Star 了 bio/project", message)
        self.assertIn("https://github.com/bio/project", message)


if __name__ == "__main__":
    unittest.main()
