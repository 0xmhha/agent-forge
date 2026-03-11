"""Tests for GitHub monitors — RED phase.

Monitors watch for changes and sync them as tasks.
Each monitor converts GitHub data into the unified Task format.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.task.models import TaskStore
from shared.types import TaskStatus, TaskType, ToolSource


class TestIssueMonitor:
    """Issue monitor should sync GitHub issues as tasks."""

    @pytest.fixture
    def monitor(self):
        from github.monitors.issue_monitor import IssueMonitor

        mock_client = AsyncMock()
        mock_task_manager = MagicMock()
        return IssueMonitor(client=mock_client, task_manager=mock_task_manager)

    @pytest.mark.asyncio
    async def test_sync_creates_tasks_from_issues(self, monitor):
        """Each open issue should become a task."""
        monitor._client.list_issues.return_value = [
            {
                "number": 42,
                "title": "Fix auth timeout",
                "author": "alice",
                "state": "open",
                "labels": ["bug", "priority:high"],
                "url": "https://github.com/org/repo/issues/42",
                "created_at": "2026-03-10T10:00:00Z",
            },
            {
                "number": 43,
                "title": "Add dark mode",
                "author": "carol",
                "state": "open",
                "labels": ["enhancement"],
                "url": "https://github.com/org/repo/issues/43",
                "created_at": "2026-03-11T09:00:00Z",
            },
        ]

        result = await monitor.sync("org/repo")

        assert result.success is True
        assert monitor._task_manager.sync_task.call_count == 2

        first_call = monitor._task_manager.sync_task.call_args_list[0]
        assert first_call.kwargs["source"] == ToolSource.GITHUB
        assert first_call.kwargs["task_type"] == TaskType.ISSUE
        assert first_call.kwargs["source_id"] == "42"
        assert first_call.kwargs["title"] == "Fix auth timeout"

    @pytest.mark.asyncio
    async def test_sync_maps_priority_from_labels(self, monitor):
        """Labels like 'priority:high' should map to TaskPriority."""
        monitor._client.list_issues.return_value = [
            {
                "number": 1,
                "title": "Critical bug",
                "author": "x",
                "state": "open",
                "labels": ["bug", "priority:critical"],
                "url": "https://github.com/org/repo/issues/1",
                "created_at": "2026-03-11T10:00:00Z",
            },
        ]

        await monitor.sync("org/repo")

        call_kwargs = monitor._task_manager.sync_task.call_args.kwargs
        assert call_kwargs["priority"].value == "critical"

    @pytest.mark.asyncio
    async def test_sync_empty_issues(self, monitor):
        """No issues should result in zero sync calls."""
        monitor._client.list_issues.return_value = []

        result = await monitor.sync("org/repo")

        assert result.success is True
        assert result.data["synced"] == 0
        assert monitor._task_manager.sync_task.call_count == 0


class TestPRMonitor:
    """PR monitor should sync pull requests as tasks."""

    @pytest.fixture
    def monitor(self):
        from github.monitors.pr_monitor import PRMonitor

        mock_client = AsyncMock()
        mock_task_manager = MagicMock()
        return PRMonitor(client=mock_client, task_manager=mock_task_manager)

    @pytest.mark.asyncio
    async def test_sync_creates_tasks_from_prs(self, monitor):
        """Each open PR should become a task of type PR."""
        monitor._client.list_prs.return_value = [
            {
                "number": 100,
                "title": "Fix auth token expiry",
                "author": "bob",
                "state": "open",
                "head_branch": "fix/auth-timeout",
                "base_branch": "main",
                "url": "https://github.com/org/repo/pull/100",
                "created_at": "2026-03-11T10:00:00Z",
                "draft": False,
            },
        ]

        result = await monitor.sync("org/repo")

        assert result.success is True
        call_kwargs = monitor._task_manager.sync_task.call_args.kwargs
        assert call_kwargs["task_type"] == TaskType.PR
        assert call_kwargs["source_id"] == "100"

    @pytest.mark.asyncio
    async def test_sync_skips_draft_prs(self, monitor):
        """Draft PRs should not be synced as tasks."""
        monitor._client.list_prs.return_value = [
            {
                "number": 101,
                "title": "WIP: Refactor",
                "author": "dave",
                "state": "open",
                "head_branch": "refactor/wip",
                "base_branch": "main",
                "url": "https://github.com/org/repo/pull/101",
                "created_at": "2026-03-11T10:00:00Z",
                "draft": True,
            },
        ]

        result = await monitor.sync("org/repo")

        assert result.data["synced"] == 0
        assert monitor._task_manager.sync_task.call_count == 0


class TestCIMonitor:
    """CI monitor should sync CI failures as tasks."""

    @pytest.fixture
    def monitor(self):
        from github.monitors.ci_monitor import CIMonitor

        mock_client = AsyncMock()
        mock_task_manager = MagicMock()
        return CIMonitor(client=mock_client, task_manager=mock_task_manager)

    @pytest.mark.asyncio
    async def test_sync_creates_task_from_failure(self, monitor):
        """A failed CI run should create a CI_FAILURE task."""
        monitor._client.get_ci_status.return_value = {
            "run_id": 9001,
            "sha": "abc123",
            "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [
                {"name": "test", "conclusion": "failure"},
            ],
        }

        result = await monitor.sync("org/repo", ref="abc123")

        assert result.success is True
        call_kwargs = monitor._task_manager.sync_task.call_args.kwargs
        assert call_kwargs["task_type"] == TaskType.CI_FAILURE
        assert "test" in call_kwargs["title"].lower() or "CI" in call_kwargs["title"]

    @pytest.mark.asyncio
    async def test_sync_skips_successful_runs(self, monitor):
        """Successful CI runs should not create tasks."""
        monitor._client.get_ci_status.return_value = {
            "run_id": 9002,
            "sha": "def456",
            "conclusion": "success",
            "url": "https://github.com/org/repo/actions/runs/9002",
            "failed_jobs": [],
        }

        result = await monitor.sync("org/repo", ref="def456")

        assert result.success is True
        assert result.data["synced"] == 0
        assert monitor._task_manager.sync_task.call_count == 0

    @pytest.mark.asyncio
    async def test_sync_neutral_no_runs(self, monitor):
        """Neutral status (no runs) should not create tasks."""
        monitor._client.get_ci_status.return_value = {
            "run_id": None,
            "sha": "xyz",
            "conclusion": "neutral",
            "url": "",
            "failed_jobs": [],
        }

        result = await monitor.sync("org/repo", ref="xyz")

        assert result.data["synced"] == 0
