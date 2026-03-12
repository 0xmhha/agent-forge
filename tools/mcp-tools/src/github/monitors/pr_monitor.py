"""PR monitor — syncs GitHub pull requests as unified tasks."""

import logging

from github.client import GitHubClient
from shared.task.manager import TaskManager
from shared.types import TaskPriority, TaskType, ToolResult, ToolSource

logger = logging.getLogger(__name__)


class PRMonitor:
    """Watches GitHub PRs and syncs non-draft PRs as tasks."""

    def __init__(self, client: GitHubClient, task_manager: TaskManager) -> None:
        self._client = client
        self._task_manager = task_manager

    async def sync(self, repo: str, state: str = "open") -> ToolResult:
        """Sync all non-draft PRs from a repo into the task store."""
        prs = await self._client.list_prs(repo, state=state)
        synced = 0

        for pr in prs:
            if pr.get("draft", False):
                continue

            self._task_manager.sync_task(
                source=ToolSource.GITHUB,
                source_id=str(pr["number"]),
                task_type=TaskType.PR,
                title=pr["title"],
                source_url=pr.get("url", ""),
                priority=TaskPriority.MEDIUM,
                metadata={
                    "author": pr.get("author", ""),
                    "head_branch": pr.get("head_branch", ""),
                    "base_branch": pr.get("base_branch", ""),
                    "repo": repo,
                },
            )
            synced += 1

        return ToolResult(
            success=True,
            data={"synced": synced, "repo": repo, "state": state},
        )
