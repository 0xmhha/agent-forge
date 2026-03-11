"""Tests for GitHub API client — RED phase.

GitHub client wraps the GitHub REST API. Uses PAT or OAuth token.
Returns sanitized data — no auth tokens in responses.
"""

from unittest.mock import AsyncMock

import pytest


SAMPLE_ISSUES = [
    {
        "number": 42,
        "title": "Fix authentication timeout",
        "state": "open",
        "user": {"login": "alice"},
        "labels": [{"name": "bug"}, {"name": "priority:high"}],
        "created_at": "2026-03-10T10:00:00Z",
        "updated_at": "2026-03-11T08:00:00Z",
        "body": "Auth tokens expire after 5 minutes instead of 30.",
        "html_url": "https://github.com/org/repo/issues/42",
        "comments": 3,
        "assignees": [{"login": "bob"}],
    },
    {
        "number": 43,
        "title": "Add dark mode",
        "state": "open",
        "user": {"login": "carol"},
        "labels": [{"name": "enhancement"}],
        "created_at": "2026-03-11T09:00:00Z",
        "updated_at": "2026-03-11T09:00:00Z",
        "body": "Please add dark mode support.",
        "html_url": "https://github.com/org/repo/issues/43",
        "comments": 0,
        "assignees": [],
    },
]

SAMPLE_ISSUE_DETAIL = SAMPLE_ISSUES[0]

SAMPLE_PRS = [
    {
        "number": 100,
        "title": "Fix auth token expiry",
        "state": "open",
        "user": {"login": "bob"},
        "labels": [{"name": "bugfix"}],
        "created_at": "2026-03-11T10:00:00Z",
        "updated_at": "2026-03-11T12:00:00Z",
        "body": "Fixes #42. Extends token TTL to 30 minutes.",
        "html_url": "https://github.com/org/repo/pull/100",
        "head": {"ref": "fix/auth-timeout", "sha": "abc123"},
        "base": {"ref": "main", "sha": "def456"},
        "merged": False,
        "draft": False,
        "mergeable": True,
        "additions": 15,
        "deletions": 3,
        "changed_files": 2,
    },
]

SAMPLE_PR_DETAIL = SAMPLE_PRS[0]

SAMPLE_PR_FILES = [
    {
        "filename": "src/auth/token.py",
        "status": "modified",
        "additions": 10,
        "deletions": 2,
        "patch": "@@ -42,7 +42,7 @@ def token_ttl():\n-    return 300\n+    return 1800",
    },
    {
        "filename": "tests/test_auth.py",
        "status": "modified",
        "additions": 5,
        "deletions": 1,
        "patch": "@@ -10,3 +10,7 @@ def test_token():\n+    assert ttl == 1800",
    },
]

SAMPLE_CI_RUNS = {
    "workflow_runs": [
        {
            "id": 9001,
            "name": "CI",
            "status": "completed",
            "conclusion": "failure",
            "head_sha": "abc123",
            "html_url": "https://github.com/org/repo/actions/runs/9001",
            "created_at": "2026-03-11T11:00:00Z",
            "updated_at": "2026-03-11T11:05:00Z",
        },
    ],
}

SAMPLE_CI_JOBS = {
    "jobs": [
        {
            "id": 50001,
            "name": "test",
            "status": "completed",
            "conclusion": "failure",
            "steps": [
                {"name": "Run tests", "status": "completed", "conclusion": "failure"},
            ],
        },
        {
            "id": 50002,
            "name": "lint",
            "status": "completed",
            "conclusion": "success",
            "steps": [],
        },
    ],
}


class TestGitHubClient:
    """GitHub client should provide read-only access to repos."""

    @pytest.fixture
    def client(self):
        from github.client import GitHubClient

        return GitHubClient(token="ghp_test_token_1234567890")

    @pytest.mark.asyncio
    async def test_list_issues(self, client):
        """list_issues should return simplified issue metadata."""
        with _patch_request(client, SAMPLE_ISSUES) as mock:
            issues = await client.list_issues("org/repo")

        assert len(issues) == 2
        assert issues[0]["number"] == 42
        assert issues[0]["title"] == "Fix authentication timeout"
        assert issues[0]["author"] == "alice"
        assert "bug" in issues[0]["labels"]

    @pytest.mark.asyncio
    async def test_list_issues_with_filters(self, client):
        """list_issues should pass state and labels to API."""
        with _patch_request(client, [SAMPLE_ISSUES[0]]) as mock:
            await client.list_issues("org/repo", state="open", labels=["bug"])

        call_kwargs = mock.call_args
        assert "state=open" in str(call_kwargs) or call_kwargs[1].get("params", {}).get("state") == "open"

    @pytest.mark.asyncio
    async def test_list_issues_empty(self, client):
        """list_issues returns empty list when no issues match."""
        with _patch_request(client, []):
            issues = await client.list_issues("org/repo")

        assert issues == []

    @pytest.mark.asyncio
    async def test_get_issue(self, client):
        """get_issue should return full issue detail with body."""
        with _patch_request(client, SAMPLE_ISSUE_DETAIL):
            issue = await client.get_issue("org/repo", 42)

        assert issue["number"] == 42
        assert issue["body"] == "Auth tokens expire after 5 minutes instead of 30."
        assert issue["comment_count"] == 3

    @pytest.mark.asyncio
    async def test_list_prs(self, client):
        """list_prs should return simplified PR metadata."""
        with _patch_request(client, SAMPLE_PRS):
            prs = await client.list_prs("org/repo")

        assert len(prs) == 1
        assert prs[0]["number"] == 100
        assert prs[0]["head_branch"] == "fix/auth-timeout"

    @pytest.mark.asyncio
    async def test_get_pr_with_files(self, client):
        """get_pr should include changed files and diff summary."""
        with _patch_request_sequence(client, [SAMPLE_PR_DETAIL, SAMPLE_PR_FILES]):
            pr = await client.get_pr("org/repo", 100)

        assert pr["number"] == 100
        assert pr["additions"] == 15
        assert len(pr["files"]) == 2
        assert pr["files"][0]["filename"] == "src/auth/token.py"

    @pytest.mark.asyncio
    async def test_get_ci_status(self, client):
        """get_ci_status should return workflow run results with failed jobs."""
        with _patch_request_sequence(client, [SAMPLE_CI_RUNS, SAMPLE_CI_JOBS]):
            ci = await client.get_ci_status("org/repo", "abc123")

        assert ci["conclusion"] == "failure"
        assert len(ci["failed_jobs"]) == 1
        assert ci["failed_jobs"][0]["name"] == "test"

    @pytest.mark.asyncio
    async def test_get_ci_status_no_runs(self, client):
        """get_ci_status returns neutral when no runs found."""
        with _patch_request(client, {"workflow_runs": []}):
            ci = await client.get_ci_status("org/repo", "abc123")

        assert ci["conclusion"] == "neutral"
        assert ci["failed_jobs"] == []

    @pytest.mark.asyncio
    async def test_no_token_in_responses(self, client):
        """Responses must NEVER contain auth tokens."""
        with _patch_request(client, SAMPLE_ISSUE_DETAIL):
            result = await client.get_issue("org/repo", 42)

        result_str = str(result)
        assert "ghp_" not in result_str
        assert "token" not in result_str.lower() or "timeout" in result_str.lower()

    def test_auth_header_stored_internally(self, client):
        """Client should store auth header but never expose it."""
        assert "ghp_test_token_1234567890" in client._auth_header


def _patch_request(client, return_value):
    """Patch client._request to return a fixed value."""
    from unittest.mock import patch

    mock = AsyncMock(return_value=return_value)
    return patch.object(client, "_request", mock)


def _patch_request_sequence(client, return_values):
    """Patch client._request to return values in sequence."""
    from unittest.mock import patch

    mock = AsyncMock(side_effect=return_values)
    return patch.object(client, "_request", mock)
