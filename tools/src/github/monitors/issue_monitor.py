"""Issue monitor — syncs GitHub issues as unified tasks."""

import logging

from github.client import GitHubClient
from shared.task.manager import TaskManager
from shared.types import TaskPriority, TaskType, ToolResult, ToolSource

logger = logging.getLogger(__name__)

_PRIORITY_LABEL_MAP = {
    "priority:critical": TaskPriority.CRITICAL,
    "priority:high": TaskPriority.HIGH,
    "priority:medium": TaskPriority.MEDIUM,
    "priority:low": TaskPriority.LOW,
    "critical": TaskPriority.CRITICAL,
    "high": TaskPriority.HIGH,
}


class IssueMonitor:
    """Watches GitHub issues and syncs them as tasks."""

    def __init__(self, client: GitHubClient, task_manager: TaskManager) -> None:
        self._client = client
        self._task_manager = task_manager

    async def sync(self, repo: str, state: str = "open") -> ToolResult:
        """Sync all matching issues from a repo into the task store."""
        issues = await self._client.list_issues(repo, state=state)
        synced = 0

        for issue in issues:
            priority = _extract_priority(issue.get("labels", []))
            self._task_manager.sync_task(
                source=ToolSource.GITHUB,
                source_id=str(issue["number"]),
                task_type=TaskType.ISSUE,
                title=issue["title"],
                source_url=issue.get("url", ""),
                priority=priority,
                metadata={
                    "author": issue.get("author", ""),
                    "labels": issue.get("labels", []),
                    "repo": repo,
                },
            )
            synced += 1

        return ToolResult(
            success=True,
            data={"synced": synced, "repo": repo, "state": state},
        )


def _extract_priority(labels: list[str]) -> TaskPriority:
    """Map GitHub labels to task priority. Defaults to MEDIUM."""
    for label in labels:
        normalized = label.lower()
        if normalized in _PRIORITY_LABEL_MAP:
            return _PRIORITY_LABEL_MAP[normalized]
    return TaskPriority.MEDIUM
