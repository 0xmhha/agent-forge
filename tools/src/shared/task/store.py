"""File-based task persistence — JSON files in a configurable directory."""

import json
from pathlib import Path

from shared.task.models import TaskStore
from shared.types import ToolSource


class FileTaskStore:
    """Read/write TaskStore instances as JSON files.

    Each source gets its own file: tasks/{source}.json
    Files are git-trackable and human-readable.
    """

    def __init__(self, store_dir: str | Path | None = None) -> None:
        self._store_dir = Path(store_dir) if store_dir else Path("data/tasks")
        self._store_dir.mkdir(parents=True, exist_ok=True)

    def load(self, source: ToolSource) -> TaskStore:
        """Load tasks for a source. Returns empty store if file doesn't exist."""
        path = self._file_path(source)
        if not path.exists():
            return TaskStore(source=source)

        raw = json.loads(path.read_text(encoding="utf-8"))
        return TaskStore.model_validate(raw)

    def save(self, store: TaskStore) -> Path:
        """Persist the task store to disk. Returns the file path."""
        path = self._file_path(store.source)
        content = store.model_dump_json(indent=2)
        path.write_text(content, encoding="utf-8")
        return path

    def list_sources(self) -> list[ToolSource]:
        """List all sources that have stored tasks."""
        sources = []
        for path in self._store_dir.glob("*.json"):
            stem = path.stem
            try:
                sources.append(ToolSource(stem))
            except ValueError:
                continue
        return sources

    def _file_path(self, source: ToolSource) -> Path:
        return self._store_dir / f"{source.value}.json"
