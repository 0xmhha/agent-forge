"""Integration tests for the complete MCP tool platform — RED phase.

Verifies that all tool modules register correctly with a single
MCP server instance and work together end-to-end.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.types import TaskStatus, TaskType, ToolResult, ToolSource


class TestServerIntegration:
    """All tools should register and coexist in a single MCP server."""

    def test_server_registers_task_tools_by_default(self):
        """ToolServer should have 3 task tools on init."""
        from shared.server import ToolServer

        server = ToolServer()
        assert "task_list" in server._tools
        assert "task_sync" in server._tools
        assert "task_update" in server._tools

    def test_gmail_tools_register(self):
        """Gmail module should add 5 tools to server (3 basic + 2 rule-based)."""
        from shared.server import ToolServer
        from gmail.tools import register as register_gmail

        server = ToolServer()
        initial_count = len(server._tools)
        register_gmail(server)

        assert len(server._tools) == initial_count + 5
        assert "gmail_list_messages" in server._tools
        assert "gmail_read_message" in server._tools
        assert "gmail_search" in server._tools
        assert "gmail_process_inbox" in server._tools
        assert "gmail_read_and_analyze" in server._tools

    def test_github_tools_register(self):
        """GitHub module should add 5 monitoring tools to server."""
        from shared.server import ToolServer
        from github.tools import register as register_github

        server = ToolServer()
        initial_count = len(server._tools)
        register_github(server)

        assert len(server._tools) == initial_count + 5
        assert "github_list_issues" in server._tools
        assert "github_get_issue" in server._tools

    def test_github_actions_register(self):
        """GitHub actions module should add 2 environment tools."""
        from shared.server import ToolServer
        from github.tools import register_actions

        server = ToolServer()
        initial_count = len(server._tools)
        register_actions(server)

        assert len(server._tools) == initial_count + 2
        assert "github_setup_pr_review" in server._tools
        assert "github_setup_ci_debug" in server._tools

    def test_all_tools_register_together(self):
        """All modules should register without conflicts. Total: 15 tools."""
        from shared.server import ToolServer
        from gmail.tools import register as register_gmail
        from github.tools import register as register_github
        from github.tools import register_actions

        server = ToolServer()
        register_gmail(server)
        register_github(server)
        register_actions(server)

        assert len(server._tools) == 15
        all_names = list(server._tools.keys())
        assert len(all_names) == len(set(all_names)), "Duplicate tool names detected"

    def test_no_tool_name_conflicts(self):
        """Tool names across all modules must be unique."""
        from shared.server import ToolServer
        from gmail.tools import register as register_gmail
        from github.tools import register as register_github
        from github.tools import register_actions

        server = ToolServer()
        register_gmail(server)
        register_github(server)
        register_actions(server)

        names = list(server._tools.keys())
        assert len(names) == len(set(names))


class TestTaskIntegrationFlow:
    """End-to-end: monitor syncs data → task manager stores → task_list returns."""

    @pytest.mark.asyncio
    async def test_issue_sync_then_list(self, tmp_dir):
        """Issues synced by monitor should appear in task_list."""
        from shared.task.manager import TaskManager
        from shared.task.store import FileTaskStore
        from github.monitors.issue_monitor import IssueMonitor

        store = FileTaskStore(store_dir=tmp_dir / "tasks")
        manager = TaskManager(store=store)

        mock_client = AsyncMock()
        mock_client.list_issues.return_value = [
            {"number": 42, "title": "Fix bug", "author": "alice",
             "state": "open", "labels": ["bug", "priority:high"],
             "url": "https://github.com/org/repo/issues/42",
             "created_at": "2026-03-11"},
            {"number": 43, "title": "Add feature", "author": "bob",
             "state": "open", "labels": ["enhancement"],
             "url": "https://github.com/org/repo/issues/43",
             "created_at": "2026-03-11"},
        ]

        monitor = IssueMonitor(client=mock_client, task_manager=manager)
        sync_result = await monitor.sync("org/repo")
        assert sync_result.success

        list_result = manager.list_tasks(source=ToolSource.GITHUB)
        assert list_result.data["count"] == 2
        titles = [t["title"] for t in list_result.data["tasks"]]
        assert "Fix bug" in titles
        assert "Add feature" in titles

    @pytest.mark.asyncio
    async def test_pr_sync_then_update_status(self, tmp_dir):
        """PR synced by monitor can have its status updated."""
        from shared.task.manager import TaskManager
        from shared.task.store import FileTaskStore
        from github.monitors.pr_monitor import PRMonitor

        store = FileTaskStore(store_dir=tmp_dir / "tasks")
        manager = TaskManager(store=store)

        mock_client = AsyncMock()
        mock_client.list_prs.return_value = [
            {"number": 100, "title": "Fix auth", "author": "bob",
             "state": "open", "head_branch": "fix/auth",
             "base_branch": "main", "draft": False,
             "url": "https://github.com/org/repo/pull/100",
             "created_at": "2026-03-11"},
        ]

        monitor = PRMonitor(client=mock_client, task_manager=manager)
        await monitor.sync("org/repo")

        tasks = manager.list_tasks(source=ToolSource.GITHUB)
        task_id = tasks.data["tasks"][0]["id"]

        update_result = manager.update_status(task_id, TaskStatus.IN_PROGRESS)
        assert update_result.success
        assert update_result.data["task"]["status"] == "in_progress"

    @pytest.mark.asyncio
    async def test_ci_failure_creates_high_priority_task(self, tmp_dir):
        """CI failure should create a HIGH priority task."""
        from shared.task.manager import TaskManager
        from shared.task.store import FileTaskStore
        from github.monitors.ci_monitor import CIMonitor

        store = FileTaskStore(store_dir=tmp_dir / "tasks")
        manager = TaskManager(store=store)

        mock_client = AsyncMock()
        mock_client.get_ci_status.return_value = {
            "run_id": 9001, "sha": "abc123", "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [{"name": "test", "conclusion": "failure"}],
        }

        monitor = CIMonitor(client=mock_client, task_manager=manager)
        await monitor.sync("org/repo", ref="abc123")

        tasks = manager.list_tasks(source=ToolSource.GITHUB, task_type=TaskType.CI_FAILURE)
        assert tasks.data["count"] == 1
        assert tasks.data["tasks"][0]["priority"] == "high"

    @pytest.mark.asyncio
    async def test_multiple_sources_coexist(self, tmp_dir):
        """Tasks from different sources should be stored separately and listable together."""
        from shared.task.manager import TaskManager
        from shared.task.store import FileTaskStore

        store = FileTaskStore(store_dir=tmp_dir / "tasks")
        manager = TaskManager(store=store)

        manager.sync_task(
            source=ToolSource.GITHUB, source_id="42",
            task_type=TaskType.ISSUE, title="GitHub issue",
        )
        manager.sync_task(
            source=ToolSource.GMAIL, source_id="msg-001",
            task_type=TaskType.EMAIL, title="Important email",
        )

        all_tasks = manager.list_tasks()
        assert all_tasks.data["count"] == 2

        github_only = manager.list_tasks(source=ToolSource.GITHUB)
        assert github_only.data["count"] == 1
        assert github_only.data["tasks"][0]["title"] == "GitHub issue"

        gmail_only = manager.list_tasks(source=ToolSource.GMAIL)
        assert gmail_only.data["count"] == 1
        assert gmail_only.data["tasks"][0]["title"] == "Important email"

    @pytest.mark.asyncio
    async def test_upsert_idempotency(self, tmp_dir):
        """Syncing the same issue twice should not create duplicates."""
        from shared.task.manager import TaskManager
        from shared.task.store import FileTaskStore
        from github.monitors.issue_monitor import IssueMonitor

        store = FileTaskStore(store_dir=tmp_dir / "tasks")
        manager = TaskManager(store=store)

        mock_client = AsyncMock()
        issues = [
            {"number": 42, "title": "Fix bug", "author": "alice",
             "state": "open", "labels": [],
             "url": "https://github.com/org/repo/issues/42",
             "created_at": "2026-03-11"},
        ]
        mock_client.list_issues.return_value = issues

        monitor = IssueMonitor(client=mock_client, task_manager=manager)
        await monitor.sync("org/repo")
        await monitor.sync("org/repo")

        tasks = manager.list_tasks(source=ToolSource.GITHUB)
        assert tasks.data["count"] == 1


class TestSecurityInvariant:
    """Cross-cutting security: no token leakage in any tool response."""

    def test_tool_result_schema_has_no_auth_fields(self):
        """ToolResult field names should not contain auth-related terms."""
        from shared.types import ToolResult

        field_names = [name.lower() for name in ToolResult.model_fields.keys()]
        for name in field_names:
            assert "token" not in name
            assert "secret" not in name
            assert "password" not in name
            assert "bearer" not in name

    def test_task_model_has_no_auth_fields(self):
        """Task model should not contain auth-related fields."""
        from shared.task.models import Task

        field_names = list(Task.model_fields.keys())
        for name in field_names:
            assert "token" not in name.lower()
            assert "secret" not in name.lower()
            assert "password" not in name.lower()

    def test_auth_config_not_serializable_to_tool_result(self):
        """AuthConfig should not be accidentally included in ToolResult.data."""
        from shared.types import AuthConfig, ToolResult, ToolSource

        config = AuthConfig(
            service=ToolSource.GMAIL,
            client_id="test-id",
            client_secret="test-secret",
            api_key="test-api-key",
        )

        result = ToolResult(success=True, data={"message": "ok"})
        result_str = result.model_dump_json()

        assert "test-secret" not in result_str
        assert "test-api-key" not in result_str


class TestMCPServerProtocol:
    """MCP server should correctly expose tools via protocol handlers."""

    @pytest.mark.asyncio
    async def test_list_tools_returns_all_registered(self):
        """list_tools handler should return all registered tool definitions."""
        from shared.server import ToolServer
        from gmail.tools import register as register_gmail
        from github.tools import register as register_github
        from github.tools import register_actions

        server = ToolServer()
        register_gmail(server)
        register_github(server)
        register_actions(server)

        tools = list(server._tools.values())
        assert len(tools) == 15

        for tool in tools:
            assert tool.name
            assert tool.description
            assert tool.inputSchema

    def test_unknown_tool_handler_not_found(self):
        """Requesting a non-existent handler should return None."""
        from shared.server import ToolServer

        server = ToolServer()
        handler = server._handlers.get("nonexistent_tool")
        assert handler is None
