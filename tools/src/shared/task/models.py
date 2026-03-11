"""Pydantic models for the unified task management system.

These models serve as both runtime validation and JSON Schema source
(via model_json_schema()). All tools share this common task format.
"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from shared.types import TaskPriority, TaskStatus, TaskType, ToolSource


class Task(BaseModel):
    """A single task synchronized from an external source."""

    id: str = Field(description="Unique task identifier (e.g. TASK-001)")
    type: TaskType = Field(description="Task category")
    status: TaskStatus = Field(default=TaskStatus.OPEN)
    priority: TaskPriority = Field(default=TaskPriority.MEDIUM)
    title: str
    source: ToolSource
    source_url: str = Field(default="", description="Link to the original item")
    source_id: str = Field(default="", description="ID in the source system")
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
    metadata: dict[str, Any] = Field(default_factory=dict)


class TaskStore(BaseModel):
    """Collection of tasks from a single source, persisted as JSON."""

    version: str = "1.0"
    source: ToolSource
    tasks: list[Task] = Field(default_factory=list)

    def find_by_source_id(self, source_id: str) -> Task | None:
        """Look up a task by its external source ID."""
        for task in self.tasks:
            if task.source_id == source_id:
                return task
        return None

    def upsert(self, task: Task) -> Task:
        """Insert or update a task based on source_id match."""
        existing = self.find_by_source_id(task.source_id)
        if existing:
            idx = self.tasks.index(existing)
            updated = task.model_copy(update={"id": existing.id})
            new_tasks = list(self.tasks)
            new_tasks[idx] = updated
            self.tasks = new_tasks
            return updated
        self.tasks = [*self.tasks, task]
        return task

    def filter_tasks(
        self,
        *,
        status: TaskStatus | None = None,
        task_type: TaskType | None = None,
        priority: TaskPriority | None = None,
    ) -> list[Task]:
        """Return tasks matching the given filters."""
        result = self.tasks
        if status is not None:
            result = [t for t in result if t.status == status]
        if task_type is not None:
            result = [t for t in result if t.type == task_type]
        if priority is not None:
            result = [t for t in result if t.priority == priority]
        return result
