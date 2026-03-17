"""Tests for FileTaskStore — JSON file-based task persistence."""

import pytest

from shared.task.models import Task, TaskStore
from shared.task.store import FileTaskStore
from shared.types import TaskPriority, TaskStatus, TaskType, ToolSource


def _make_task(source_id: str = "42", title: str = "Fix bug") -> Task:
    return Task(
        id=f"TASK-{source_id}",
        type=TaskType.ISSUE,
        source=ToolSource.GITHUB,
        source_id=source_id,
        title=title,
    )


class TestFileTaskStoreRoundTrip:
    """TaskStore should survive save → load cycle."""

    def test_save_and_load(self, task_store):
        store = TaskStore(source=ToolSource.GITHUB, tasks=[_make_task()])
        task_store.save(store)

        loaded = task_store.load(ToolSource.GITHUB)
        assert len(loaded.tasks) == 1
        assert loaded.tasks[0].title == "Fix bug"

    def test_load_nonexistent_returns_empty_store(self, task_store):
        loaded = task_store.load(ToolSource.GMAIL)

        assert loaded.source == ToolSource.GMAIL
        assert loaded.tasks == []

    def test_overwrite_replaces_store(self, task_store):
        store_v1 = TaskStore(source=ToolSource.GITHUB, tasks=[_make_task()])
        task_store.save(store_v1)

        store_v2 = TaskStore(
            source=ToolSource.GITHUB,
            tasks=[_make_task("99", "New task")],
        )
        task_store.save(store_v2)

        loaded = task_store.load(ToolSource.GITHUB)
        assert len(loaded.tasks) == 1
        assert loaded.tasks[0].title == "New task"

    def test_different_sources_stored_separately(self, task_store):
        github_store = TaskStore(
            source=ToolSource.GITHUB, tasks=[_make_task("1", "GitHub task")]
        )
        gmail_store = TaskStore(
            source=ToolSource.GMAIL,
            tasks=[Task(
                id="TASK-email", type=TaskType.EMAIL, source=ToolSource.GMAIL,
                source_id="msg-1", title="Gmail task",
            )],
        )
        task_store.save(github_store)
        task_store.save(gmail_store)

        assert task_store.load(ToolSource.GITHUB).tasks[0].title == "GitHub task"
        assert task_store.load(ToolSource.GMAIL).tasks[0].title == "Gmail task"


class TestFileTaskStoreListSources:
    def test_list_sources(self, task_store):
        task_store.save(TaskStore(source=ToolSource.GITHUB))
        task_store.save(TaskStore(source=ToolSource.GMAIL))

        sources = task_store.list_sources()
        assert set(sources) == {ToolSource.GITHUB, ToolSource.GMAIL}

    def test_empty_store_no_sources(self, task_store):
        assert task_store.list_sources() == []


class TestFileTaskStoreDirectoryCreation:
    def test_creates_store_directory(self, tmp_dir):
        store_path = tmp_dir / "new_tasks"
        store = FileTaskStore(store_dir=store_path)
        store.save(TaskStore(source=ToolSource.GITHUB, tasks=[_make_task()]))

        assert store_path.exists()
        assert store.load(ToolSource.GITHUB).tasks[0].title == "Fix bug"
