"""Task manager — CRUD operations over the file-based task store."""

from datetime import datetime

from shared.task.models import Task, TaskStore
from shared.task.store import FileTaskStore
from shared.types import TaskPriority, TaskStatus, TaskType, ToolResult, ToolSource


class TaskManager:
    """Provides task operations exposed as MCP tools.

    All mutations create new objects (immutability principle).
    """

    def __init__(self, store: FileTaskStore | None = None) -> None:
        self._store = store or FileTaskStore()
        self._counter: dict[str, int] = {}

    def list_tasks(
        self,
        source: ToolSource | None = None,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
    ) -> ToolResult:
        """List tasks with optional filters."""
        sources = [source] if source else self._store.list_sources()
        all_tasks: list[dict] = []

        for src in sources:
            task_store = self._store.load(src)
            filtered = task_store.filter_tasks(status=status, task_type=task_type)
            all_tasks.extend(t.model_dump(mode="json") for t in filtered)

        return ToolResult(success=True, data={"tasks": all_tasks, "count": len(all_tasks)})

    def sync_task(
        self,
        source: ToolSource,
        source_id: str,
        task_type: TaskType,
        title: str,
        *,
        source_url: str = "",
        priority: TaskPriority = TaskPriority.MEDIUM,
        metadata: dict | None = None,
    ) -> ToolResult:
        """Sync a single task from an external source (upsert)."""
        task_store = self._store.load(source)

        task = Task(
            id=self._next_id(source),
            type=task_type,
            status=TaskStatus.OPEN,
            priority=priority,
            title=title,
            source=source,
            source_url=source_url,
            source_id=source_id,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            metadata=metadata or {},
        )

        upserted = task_store.upsert(task)
        self._store.save(task_store)

        return ToolResult(
            success=True,
            data={"task": upserted.model_dump(mode="json"), "action": "upserted"},
        )

    def update_status(self, task_id: str, status: TaskStatus) -> ToolResult:
        """Update the status of a task by its ID."""
        for source in self._store.list_sources():
            task_store = self._store.load(source)
            for i, task in enumerate(task_store.tasks):
                if task.id == task_id:
                    updated = task.model_copy(
                        update={"status": status, "updated_at": datetime.now()}
                    )
                    new_tasks = list(task_store.tasks)
                    new_tasks[i] = updated
                    new_store = task_store.model_copy(update={"tasks": new_tasks})
                    self._store.save(new_store)
                    return ToolResult(
                        success=True,
                        data={"task": updated.model_dump(mode="json")},
                    )

        return ToolResult(success=False, error=f"Task not found: {task_id}")

    def _next_id(self, source: ToolSource) -> str:
        """Generate the next sequential task ID for a source."""
        key = source.value
        if key not in self._counter:
            task_store = self._store.load(source)
            self._counter[key] = len(task_store.tasks)
        self._counter[key] += 1
        return f"TASK-{self._counter[key]:03d}"
