"""CI monitor — syncs GitHub Actions failures as unified tasks."""

import logging

from github.client import GitHubClient
from shared.task.manager import TaskManager
from shared.types import TaskPriority, TaskType, ToolResult, ToolSource

logger = logging.getLogger(__name__)


class CIMonitor:
    """Watches GitHub Actions and syncs CI failures as tasks."""

    def __init__(self, client: GitHubClient, task_manager: TaskManager) -> None:
        self._client = client
        self._task_manager = task_manager

    async def sync(self, repo: str, ref: str = "main") -> ToolResult:
        """Check CI status for a ref and create task if failed."""
        ci = await self._client.get_ci_status(repo, ref)

        if ci["conclusion"] != "failure":
            return ToolResult(
                success=True,
                data={"synced": 0, "repo": repo, "ref": ref, "conclusion": ci["conclusion"]},
            )

        failed_names = [job["name"] for job in ci.get("failed_jobs", [])]
        title = f"CI failure: {', '.join(failed_names)}" if failed_names else "CI failure"

        self._task_manager.sync_task(
            source=ToolSource.GITHUB,
            source_id=str(ci.get("run_id", "")),
            task_type=TaskType.CI_FAILURE,
            title=title,
            source_url=ci.get("url", ""),
            priority=TaskPriority.HIGH,
            metadata={
                "sha": ci.get("sha", ""),
                "failed_jobs": failed_names,
                "repo": repo,
            },
        )

        return ToolResult(
            success=True,
            data={"synced": 1, "repo": repo, "ref": ref, "conclusion": "failure"},
        )
