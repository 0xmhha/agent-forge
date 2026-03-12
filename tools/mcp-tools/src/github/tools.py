"""GitHub MCP tool registration and handlers.

Registers 5 monitoring tools and 2 environment setup tools.
Each handler wraps GitHubClient and returns ToolResult.
Token sanitization uses the shared sanitize module.
"""

import logging
from typing import Any

from github.actions.ci_environment import CIEnvironment
from github.actions.pr_environment import PREnvironment
from github.client import GitHubClient
from shared.sanitize import sanitize
from shared.server import ToolServer
from shared.types import ToolResult

logger = logging.getLogger(__name__)

_REPO_PARAM = {
    "type": "string",
    "description": "Repository in 'owner/repo' format",
}


def register(server: ToolServer) -> None:
    """Register all GitHub monitoring tools with the MCP server.

    Creates a GitHubClient from GITHUB_TOKEN env var if available.
    Tools return clear error messages when credentials are missing.
    """
    client = _create_client()

    server.register_tool(
        name="github_list_issues",
        description="List issues for a GitHub repository",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
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
        handler=_make_handler(client, _handle_list_issues),
    )

    server.register_tool(
        name="github_get_issue",
        description="Get detailed information about a specific issue",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "issue_number": {"type": "integer", "description": "Issue number"},
            },
            "required": ["repo", "issue_number"],
        },
        handler=_make_handler(client, _handle_get_issue),
    )

    server.register_tool(
        name="github_list_prs",
        description="List pull requests for a GitHub repository",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "state": {
                    "type": "string",
                    "enum": ["open", "closed", "all"],
                    "default": "open",
                },
            },
            "required": ["repo"],
        },
        handler=_make_handler(client, _handle_list_prs),
    )

    server.register_tool(
        name="github_get_pr",
        description="Get PR details including changed files and diff",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "pr_number": {"type": "integer", "description": "PR number"},
            },
            "required": ["repo", "pr_number"],
        },
        handler=_make_handler(client, _handle_get_pr),
    )

    server.register_tool(
        name="github_get_ci_status",
        description="Get CI/CD status for a commit or branch",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "ref": {
                    "type": "string",
                    "description": "Branch name or commit SHA",
                    "default": "main",
                },
            },
            "required": ["repo"],
        },
        handler=_make_handler(client, _handle_get_ci_status),
    )


def register_actions(server: ToolServer) -> None:
    """Register environment setup tools (PR review, CI debug)."""
    client = _create_client()

    server.register_tool(
        name="github_setup_pr_review",
        description="Clone repo and checkout PR branch for code review",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "pr_number": {"type": "integer", "description": "PR number"},
                "target_dir": {"type": "string", "description": "Local directory to clone into"},
            },
            "required": ["repo", "pr_number", "target_dir"],
        },
        handler=_make_action_handler(client, "pr_review"),
    )

    server.register_tool(
        name="github_setup_ci_debug",
        description="Clone repo at failed commit and fetch CI failure logs",
        input_schema={
            "type": "object",
            "properties": {
                "repo": _REPO_PARAM,
                "run_id": {"type": "integer", "description": "GitHub Actions run ID"},
                "target_dir": {"type": "string", "description": "Local directory to clone into"},
            },
            "required": ["repo", "run_id", "target_dir"],
        },
        handler=_make_action_handler(client, "ci_debug"),
    )


def _create_client() -> GitHubClient | None:
    """Create GitHubClient from GITHUB_TOKEN env var, or None if unavailable."""
    try:
        from shared.auth.credentials import load_github_config

        config = load_github_config()
        token = config.api_key.get_secret_value()

        if not token:
            logger.warning("GitHub: no GITHUB_TOKEN — tools will return auth-required error")
            return None

        return GitHubClient(token=token)
    except Exception:
        logger.exception("GitHub client initialization failed")
        return None


def _make_handler(client: GitHubClient | None, handler_fn: Any) -> Any:
    """Wrap an async handler with client injection and error handling."""

    async def handler(**kwargs: Any) -> ToolResult:
        if client is None:
            return ToolResult(
                success=False,
                error="GitHub not configured — set GITHUB_TOKEN environment variable",
            )
        try:
            return await handler_fn(client=client, **kwargs)
        except Exception as exc:
            return ToolResult(success=False, error=sanitize(str(exc)))

    return handler


def _make_action_handler(client: GitHubClient | None, action: str) -> Any:
    """Wrap environment setup actions with client injection and error handling."""

    async def handler(**kwargs: Any) -> ToolResult:
        if client is None:
            return ToolResult(
                success=False,
                error="GitHub not configured — set GITHUB_TOKEN environment variable",
            )
        try:
            if action == "pr_review":
                env = PREnvironment(client=client)
                return await env.setup(
                    repo=kwargs["repo"],
                    pr_number=kwargs["pr_number"],
                    target_dir=kwargs["target_dir"],
                )
            if action == "ci_debug":
                env = CIEnvironment(client=client)
                return await env.setup(
                    repo=kwargs["repo"],
                    run_id=kwargs["run_id"],
                    target_dir=kwargs["target_dir"],
                )
            return ToolResult(success=False, error=f"Unknown action: {action}")
        except Exception as exc:
            return ToolResult(success=False, error=sanitize(str(exc)))

    return handler


async def _handle_list_issues(
    *, client: GitHubClient, repo: str, state: str = "open", labels: str = "",
) -> ToolResult:
    label_list = [l.strip() for l in labels.split(",") if l.strip()] if labels else None
    issues = await client.list_issues(repo, state=state, labels=label_list)
    return ToolResult(success=True, data={"issues": issues, "count": len(issues)})


async def _handle_get_issue(
    *, client: GitHubClient, repo: str, issue_number: int,
) -> ToolResult:
    issue = await client.get_issue(repo, issue_number)
    return ToolResult(success=True, data={"issue": issue})


async def _handle_list_prs(
    *, client: GitHubClient, repo: str, state: str = "open",
) -> ToolResult:
    prs = await client.list_prs(repo, state=state)
    return ToolResult(success=True, data={"prs": prs, "count": len(prs)})


async def _handle_get_pr(
    *, client: GitHubClient, repo: str, pr_number: int,
) -> ToolResult:
    pr = await client.get_pr(repo, pr_number)
    return ToolResult(success=True, data={"pr": pr})


async def _handle_get_ci_status(
    *, client: GitHubClient, repo: str, ref: str = "main",
) -> ToolResult:
    ci = await client.get_ci_status(repo, ref)
    return ToolResult(success=True, data={"ci": ci})
