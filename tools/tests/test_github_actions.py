"""Tests for GitHub environment setup actions — RED phase.

PR review: clones repo, checks out PR branch, returns workspace info.
CI debug: clones repo, fetches failed job logs, returns failure context.
"""

import os
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.types import ToolResult


class TestPREnvironment:
    """PR environment should clone and checkout a PR for review."""

    @pytest.fixture
    def pr_env(self):
        from github.actions.pr_environment import PREnvironment

        mock_client = AsyncMock()
        return PREnvironment(client=mock_client)

    @pytest.mark.asyncio
    async def test_setup_clones_and_checkouts(self, pr_env, tmp_dir):
        """setup should clone the repo and checkout the PR branch."""
        pr_env._client.get_pr.return_value = {
            "number": 100,
            "title": "Fix auth timeout",
            "head_branch": "fix/auth-timeout",
            "base_branch": "main",
            "body": "Fixes #42",
            "author": "bob",
            "additions": 15,
            "deletions": 3,
            "changed_files": 2,
            "files": [
                {"filename": "src/auth.py", "status": "modified", "additions": 10,
                 "deletions": 2, "patch": "@@ -1 +1 @@\n-old\n+new"},
                {"filename": "tests/test_auth.py", "status": "modified", "additions": 5,
                 "deletions": 1, "patch": "@@ -1 +1 @@\n-old\n+new"},
            ],
        }

        target = str(tmp_dir / "review")
        with patch("github.actions.pr_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            result = await pr_env.setup("org/repo", pr_number=100, target_dir=target)

        assert result.success is True
        assert result.data["pr"]["number"] == 100
        assert result.data["pr"]["head_branch"] == "fix/auth-timeout"
        assert len(result.data["pr"]["files"]) == 2
        assert result.data["target_dir"] == target

    @pytest.mark.asyncio
    async def test_setup_calls_git_clone_and_checkout(self, pr_env, tmp_dir):
        """setup should run git clone then git checkout."""
        pr_env._client.get_pr.return_value = {
            "number": 100,
            "title": "Fix",
            "head_branch": "fix/x",
            "base_branch": "main",
            "body": "",
            "author": "bob",
            "additions": 1,
            "deletions": 0,
            "changed_files": 1,
            "files": [],
        }

        target = str(tmp_dir / "review")
        with patch("github.actions.pr_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            await pr_env.setup("org/repo", pr_number=100, target_dir=target)

        calls = [str(c) for c in mock_git.call_args_list]
        assert any("clone" in c for c in calls), "Expected git clone call"
        assert any("fetch" in c or "checkout" in c for c in calls), "Expected checkout call"

    @pytest.mark.asyncio
    async def test_setup_returns_diff_summary(self, pr_env, tmp_dir):
        """Result should include additions/deletions summary."""
        pr_env._client.get_pr.return_value = {
            "number": 100,
            "title": "Fix",
            "head_branch": "fix/x",
            "base_branch": "main",
            "body": "",
            "author": "bob",
            "additions": 15,
            "deletions": 3,
            "changed_files": 2,
            "files": [],
        }

        target = str(tmp_dir / "review")
        with patch("github.actions.pr_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            result = await pr_env.setup("org/repo", pr_number=100, target_dir=target)

        assert result.data["pr"]["additions"] == 15
        assert result.data["pr"]["deletions"] == 3

    @pytest.mark.asyncio
    async def test_setup_clone_failure(self, pr_env, tmp_dir):
        """If git clone fails, result should indicate failure."""
        pr_env._client.get_pr.return_value = {
            "number": 100, "title": "Fix", "head_branch": "fix/x",
            "base_branch": "main", "body": "", "author": "bob",
            "additions": 0, "deletions": 0, "changed_files": 0, "files": [],
        }

        target = str(tmp_dir / "review")
        with patch("github.actions.pr_environment.run_git") as mock_git:
            mock_git.return_value = (False, "fatal: repository not found")
            result = await pr_env.setup("org/repo", pr_number=100, target_dir=target)

        assert result.success is False
        assert "repository" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_token_in_result(self, pr_env, tmp_dir):
        """Clone URL must not contain tokens."""
        pr_env._client.get_pr.return_value = {
            "number": 100, "title": "Fix", "head_branch": "fix/x",
            "base_branch": "main", "body": "", "author": "bob",
            "additions": 0, "deletions": 0, "changed_files": 0, "files": [],
        }

        target = str(tmp_dir / "review")
        with patch("github.actions.pr_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            result = await pr_env.setup("org/repo", pr_number=100, target_dir=target)

        result_str = str(result)
        assert "ghp_" not in result_str
        assert "Bearer" not in result_str


class TestCIEnvironment:
    """CI debug environment should fetch failure context."""

    @pytest.fixture
    def ci_env(self):
        from github.actions.ci_environment import CIEnvironment

        mock_client = AsyncMock()
        return CIEnvironment(client=mock_client)

    @pytest.mark.asyncio
    async def test_setup_fetches_failed_logs(self, ci_env, tmp_dir):
        """setup should fetch CI run info and failed job logs."""
        ci_env._client.get_ci_status.return_value = {
            "run_id": 9001,
            "sha": "abc123",
            "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [
                {"name": "test", "conclusion": "failure"},
            ],
        }
        ci_env._fetch_job_log = AsyncMock(return_value="FAILED: test_auth_timeout\nAssertionError: 300 != 1800")

        target = str(tmp_dir / "debug")
        with patch("github.actions.ci_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            result = await ci_env.setup("org/repo", run_id=9001, target_dir=target)

        assert result.success is True
        assert result.data["run_id"] == 9001
        assert result.data["conclusion"] == "failure"
        assert len(result.data["failed_jobs"]) == 1
        assert "AssertionError" in result.data["failed_jobs"][0]["log"]

    @pytest.mark.asyncio
    async def test_setup_clones_at_failed_sha(self, ci_env, tmp_dir):
        """Should clone the repo at the exact commit that failed."""
        ci_env._client.get_ci_status.return_value = {
            "run_id": 9001,
            "sha": "abc123",
            "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [],
        }
        ci_env._fetch_job_log = AsyncMock(return_value="")

        target = str(tmp_dir / "debug")
        with patch("github.actions.ci_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            await ci_env.setup("org/repo", run_id=9001, target_dir=target)

        calls = [str(c) for c in mock_git.call_args_list]
        assert any("abc123" in c for c in calls), "Expected checkout at failed SHA"

    @pytest.mark.asyncio
    async def test_setup_success_run_returns_no_debug(self, ci_env, tmp_dir):
        """Successful CI run should not set up debug environment."""
        ci_env._client.get_ci_status.return_value = {
            "run_id": 9002,
            "sha": "def456",
            "conclusion": "success",
            "url": "https://github.com/org/repo/actions/runs/9002",
            "failed_jobs": [],
        }

        target = str(tmp_dir / "debug")
        result = await ci_env.setup("org/repo", run_id=9002, target_dir=target)

        assert result.success is True
        assert result.data["conclusion"] == "success"
        assert result.data.get("message", "").lower().count("no failure") > 0 or \
               result.data.get("skipped", False) is True

    @pytest.mark.asyncio
    async def test_setup_clone_failure(self, ci_env, tmp_dir):
        """If git clone fails, result should indicate failure."""
        ci_env._client.get_ci_status.return_value = {
            "run_id": 9001,
            "sha": "abc123",
            "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [{"name": "test", "conclusion": "failure"}],
        }
        ci_env._fetch_job_log = AsyncMock(return_value="log")

        target = str(tmp_dir / "debug")
        with patch("github.actions.ci_environment.run_git") as mock_git:
            mock_git.return_value = (False, "fatal: unable to access")
            result = await ci_env.setup("org/repo", run_id=9001, target_dir=target)

        assert result.success is False

    @pytest.mark.asyncio
    async def test_no_token_in_logs(self, ci_env, tmp_dir):
        """Returned logs must not contain auth tokens."""
        ci_env._client.get_ci_status.return_value = {
            "run_id": 9001,
            "sha": "abc123",
            "conclusion": "failure",
            "url": "https://github.com/org/repo/actions/runs/9001",
            "failed_jobs": [{"name": "test", "conclusion": "failure"}],
        }
        ci_env._fetch_job_log = AsyncMock(
            return_value="Error with token ghp_secret123 in request"
        )

        target = str(tmp_dir / "debug")
        with patch("github.actions.ci_environment.run_git") as mock_git:
            mock_git.return_value = (True, "")
            result = await ci_env.setup("org/repo", run_id=9001, target_dir=target)

        result_str = str(result)
        assert "ghp_" not in result_str


class TestGitHubM4ToolRegistration:
    """M4 tools should register setup_pr_review and setup_ci_debug."""

    def test_register_adds_two_tools(self):
        from github.tools import register_actions

        mock_server = MagicMock()
        mock_server.task_manager = MagicMock()
        register_actions(mock_server)

        assert mock_server.register_tool.call_count == 2
        tool_names = [call.kwargs["name"] for call in mock_server.register_tool.call_args_list]
        assert "github_setup_pr_review" in tool_names
        assert "github_setup_ci_debug" in tool_names

    def test_tool_schemas_require_repo_and_target(self):
        from github.tools import register_actions

        mock_server = MagicMock()
        mock_server.task_manager = MagicMock()
        register_actions(mock_server)

        for call in mock_server.register_tool.call_args_list:
            schema = call.kwargs["input_schema"]
            assert "repo" in schema["required"]
            assert "target_dir" in schema["required"]
