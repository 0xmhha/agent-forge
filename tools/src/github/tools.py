"""GitHub MCP tool registration and handlers.

Registers 5 monitoring tools. Each handler wraps GitHubClient
and returns ToolResult. Token sanitization scrubs ghp_* patterns.
"""

import re
from typing import Any

from github.client import GitHubClient
from shared.server import ToolServer
from shared.types import ToolResult

_TOKEN_PATTERN = re.compile(r"ghp_[A-Za-z0-9]+|gho_[A-Za-z0-9]+|Bearer\s+\S+", re.IGNORECASE)


def register(server: ToolServer) -> None:
    """Register all GitHub monitoring tools with the MCP server."""
    _repo_param = {
        "type": "string",
        "description": "Repository in 'owner/repo' format",
    }

    server.register_tool(
        name="github_list_issues",
        description="List issues for a GitHub repository",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _repo_param,
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                },
                "labels": {
                    "type": "string",
                    "description": "Comma-separated label filter",
                    "default": "",
                },
            },
            "required": ["repo"],
        },
        handler=_make_stub("github_list_issues"),
    )

    server.register_tool(
        name="github_get_issue",
        description="Get detailed information about a specific issue",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _repo_param,
                "issue_number": {"type": "integer", "description": "Issue number"},
            },
            "required": ["repo", "issue_number"],
        },
        handler=_make_stub("github_get_issue"),
    )

    server.register_tool(
        name="github_list_prs",
        description="List pull requests for a GitHub repository",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _repo_param,
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                },
            },
            "required": ["repo"],
        },
        handler=_make_stub("github_list_prs"),
    )

    server.register_tool(
        name="github_get_pr",
        description="Get PR details including changed files and diff",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _repo_param,
                "pr_number": {"type": "integer", "description": "PR number"},
            },
            "required": ["repo", "pr_number"],
        },
        handler=_make_stub("github_get_pr"),
    )

    server.register_tool(
        name="github_get_ci_status",
        description="Get CI/CD status for a commit or branch",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _repo_param,
                "ref": {
                    "type": "string",
                    "description": "Branch name or commit SHA",
                    "default": "main",
                },
            },
            "required": ["repo"],
        },
        handler=_make_stub("github_get_ci_status"),
    )


async def handle_list_issues(
    *,
    client: GitHubClient,
    repo: str,
    state: str = "open",
    labels: str = "",
) -> ToolResult:
    """Handle github_list_issues tool call."""
    try:
        label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
        issues = await client.list_issues(repo, state=state, labels=label_list)
        return ToolResult(
            success=True,
            data={"issues": issues, "count": len(issues)},
        )
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_get_issue(
    *,
    client: GitHubClient,
    repo: str,
    issue_number: int,
) -> ToolResult:
    """Handle github_get_issue tool call."""
    try:
        issue = await client.get_issue(repo, issue_number)
        return ToolResult(success=True, data={"issue": issue})
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_list_prs(
    *,
    client: GitHubClient,
    repo: str,
    state: str = "open",
) -> ToolResult:
    """Handle github_list_prs tool call."""
    try:
        prs = await client.list_prs(repo, state=state)
        return ToolResult(success=True, data={"prs": prs, "count": len(prs)})
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_get_pr(
    *,
    client: GitHubClient,
    repo: str,
    pr_number: int,
) -> ToolResult:
    """Handle github_get_pr tool call."""
    try:
        pr = await client.get_pr(repo, pr_number)
        return ToolResult(success=True, data={"pr": pr})
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_get_ci_status(
    *,
    client: GitHubClient,
    repo: str,
    ref: str = "main",
) -> ToolResult:
    """Handle github_get_ci_status tool call."""
    try:
        ci = await client.get_ci_status(repo, ref)
        return ToolResult(success=True, data={"ci": ci})
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


def _sanitize_error(message: str) -> str:
    """Remove accidentally leaked tokens from error messages."""
    return _TOKEN_PATTERN.sub("[REDACTED]", message)


def _make_stub(name: str) -> Any:
    """Create a placeholder handler until client is configured."""

    def handler(**kwargs: Any) -> ToolResult:
        raise NotImplementedError(f"{name}: GitHub client not configured")

    return handler
