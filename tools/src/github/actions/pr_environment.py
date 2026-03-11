"""PR review environment — clones repo and checks out PR branch."""

import logging

from github.actions.git_utils import clone_url, run_git
from github.client import GitHubClient
from shared.types import ToolResult

logger = logging.getLogger(__name__)


class PREnvironment:
    """Sets up a local environment for reviewing a pull request.

    Clones the repo, fetches the PR branch, and returns PR metadata
    with changed files for context.
    """

    def __init__(self, client: GitHubClient) -> None:
        self._client = client

    async def setup(
        self,
        repo: str,
        pr_number: int,
        target_dir: str,
    ) -> ToolResult:
        """Clone repo and checkout PR branch at target_dir."""
        pr = await self._client.get_pr(repo, pr_number)

        url = clone_url(repo)
        success, output = await run_git("clone", "--depth=1", url, target_dir)
        if not success:
            return ToolResult(success=False, error=f"Clone failed: {output}")

        head_branch = pr["head_branch"]
        success, output = await run_git(
            "fetch", "origin", f"pull/{pr_number}/head:{head_branch}",
            cwd=target_dir,
        )
        if not success:
            return ToolResult(success=False, error=f"Fetch PR failed: {output}")

        success, output = await run_git("checkout", head_branch, cwd=target_dir)
        if not success:
            return ToolResult(success=False, error=f"Checkout failed: {output}")

        return ToolResult(
            success=True,
            data={
                "target_dir": target_dir,
                "pr": {
                    "number": pr["number"],
                    "title": pr["title"],
                    "head_branch": pr["head_branch"],
                    "base_branch": pr["base_branch"],
                    "author": pr.get("author", ""),
                    "body": pr.get("body", ""),
                    "additions": pr.get("additions", 0),
                    "deletions": pr.get("deletions", 0),
                    "changed_files": pr.get("changed_files", 0),
                    "files": pr.get("files", []),
                },
            },
        )
