"""Tests for GitHub MCP tool registration — RED phase.

Tools are the MCP interface. They delegate to GitHubClient
and return ToolResult objects.
"""

from unittest.mock import AsyncMock, MagicMock

import pytest

from shared.types import ToolResult


class TestGitHubToolRegistration:
    """GitHub tools should register correctly with MCP server."""

    def test_register_adds_five_tools(self):
        """GitHub module should register exactly 5 monitoring tools."""
        from github.tools import register

        mock_server = MagicMock()
        mock_server.task_manager = MagicMock()
        register(mock_server)

        assert mock_server.register_tool.call_count == 5
        tool_names = [call.kwargs["name"] for call in mock_server.register_tool.call_args_list]
        assert "github_list_issues" in tool_names
        assert "github_get_issue" in tool_names
        assert "github_list_prs" in tool_names
        assert "github_get_pr" in tool_names
        assert "github_get_ci_status" in tool_names

    def test_tool_schemas_require_repo(self):
        """All GitHub tools should require 'repo' parameter."""
        from github.tools import register

        mock_server = MagicMock()
        mock_server.task_manager = MagicMock()
        register(mock_server)

        for call in mock_server.register_tool.call_args_list:
            schema = call.kwargs["input_schema"]
            assert "repo" in schema["properties"], f"{call.kwargs['name']} missing repo"
            assert "repo" in schema["required"], f"{call.kwargs['name']} repo not required"


class TestGitHubToolHandlers:
    """GitHub tool handlers should return ToolResult."""

    @pytest.mark.asyncio
    async def test_handle_list_issues(self):
        from github.tools import handle_list_issues

        mock_client = AsyncMock()
        mock_client.list_issues.return_value = [
            {"number": 42, "title": "Bug", "author": "alice", "state": "open",
             "labels": ["bug"], "url": "https://github.com/o/r/issues/42",
             "created_at": "2026-03-11"},
        ]

        result = await handle_list_issues(
            client=mock_client, repo="org/repo", state="open", labels=""
        )

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert result.data["count"] == 1

    @pytest.mark.asyncio
    async def test_handle_get_issue(self):
        from github.tools import handle_get_issue

        mock_client = AsyncMock()
        mock_client.get_issue.return_value = {
            "number": 42, "title": "Bug", "body": "Details...",
            "author": "alice", "state": "open", "labels": ["bug"],
            "url": "https://github.com/o/r/issues/42",
            "comment_count": 3,
        }

        result = await handle_get_issue(
            client=mock_client, repo="org/repo", issue_number=42
        )

        assert result.success is True
        assert result.data["issue"]["body"] == "Details..."

    @pytest.mark.asyncio
    async def test_handle_list_prs(self):
        from github.tools import handle_list_prs

        mock_client = AsyncMock()
        mock_client.list_prs.return_value = [
            {"number": 100, "title": "Fix", "author": "bob", "state": "open",
             "head_branch": "fix/x", "base_branch": "main",
             "url": "https://github.com/o/r/pull/100", "draft": False,
             "created_at": "2026-03-11"},
        ]

        result = await handle_list_prs(
            client=mock_client, repo="org/repo", state="open"
        )

        assert result.success is True
        assert result.data["count"] == 1

    @pytest.mark.asyncio
    async def test_handle_get_pr(self):
        from github.tools import handle_get_pr

        mock_client = AsyncMock()
        mock_client.get_pr.return_value = {
            "number": 100, "title": "Fix", "body": "Fixes #42",
            "additions": 10, "deletions": 2, "changed_files": 1,
            "files": [{"filename": "a.py", "status": "modified",
                       "additions": 10, "deletions": 2}],
        }

        result = await handle_get_pr(
            client=mock_client, repo="org/repo", pr_number=100
        )

        assert result.success is True
        assert len(result.data["pr"]["files"]) == 1

    @pytest.mark.asyncio
    async def test_handle_get_ci_status(self):
        from github.tools import handle_get_ci_status

        mock_client = AsyncMock()
        mock_client.get_ci_status.return_value = {
            "run_id": 9001, "sha": "abc", "conclusion": "failure",
            "url": "https://github.com/o/r/actions/runs/9001",
            "failed_jobs": [{"name": "test", "conclusion": "failure"}],
        }

        result = await handle_get_ci_status(
            client=mock_client, repo="org/repo", ref="abc"
        )

        assert result.success is True
        assert result.data["ci"]["conclusion"] == "failure"

    @pytest.mark.asyncio
    async def test_handler_error_returns_failure(self):
        from github.tools import handle_list_issues

        mock_client = AsyncMock()
        mock_client.list_issues.side_effect = Exception("rate limit exceeded")

        result = await handle_list_issues(
            client=mock_client, repo="org/repo", state="", labels=""
        )

        assert result.success is False
        assert "rate limit" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_token_in_error(self):
        """Error messages must not leak tokens."""
        from github.tools import handle_list_issues

        mock_client = AsyncMock()
        mock_client.list_issues.side_effect = Exception(
            "Auth failed for ghp_secrettoken123"
        )

        result = await handle_list_issues(
            client=mock_client, repo="org/repo", state="", labels=""
        )

        assert "ghp_" not in result.error
