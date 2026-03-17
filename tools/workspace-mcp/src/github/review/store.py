"""File-based review request storage with pending/done/todo folders.

Directory structure:
    data/reviews/
        pending/   — new review requests (batch watcher creates these)
        done/      — completed reviews (moved from pending)
        todo/      — agent work documents (MCP tool creates these)
"""

import shutil
from pathlib import Path

from github.review.models import ReviewRequest

_DEFAULT_BASE = Path(__file__).resolve().parents[3] / "data" / "reviews"


class ReviewStore:
    """Manages review request files across pending/done/todo folders."""

    def __init__(self, base_dir: Path | None = None) -> None:
        self._base = base_dir or _DEFAULT_BASE
        self._pending = self._base / "pending"
        self._done = self._base / "done"
        self._todo = self._base / "todo"

        for d in (self._pending, self._done, self._todo):
            d.mkdir(parents=True, exist_ok=True)

    def save_pending(self, review: ReviewRequest) -> Path:
        """Save a new review request to pending folder. Skips if already exists."""
        path = self._pending / f"{review.slug}.md"
        if path.exists():
            return path
        path.write_text(review.to_pending_markdown(), encoding="utf-8")
        return path

    def save_todo(self, review: ReviewRequest) -> Path:
        """Save an agent todo document for a review request."""
        path = self._todo / f"newjob-{review.slug}.md"
        if path.exists():
            return path
        path.write_text(review.to_todo_markdown(), encoding="utf-8")
        return path

    def mark_done(self, slug: str) -> bool:
        """Move a review from pending to done."""
        src = self._pending / f"{slug}.md"
        if not src.exists():
            return False
        dst = self._done / f"{slug}.md"
        shutil.move(str(src), str(dst))
        return True

    def list_pending(self) -> list[dict]:
        """List all pending review requests."""
        return self._list_folder(self._pending)

    def list_done(self) -> list[dict]:
        """List all completed reviews."""
        return self._list_folder(self._done)

    def list_todo(self) -> list[dict]:
        """List all todo work documents."""
        return self._list_folder(self._todo)

    def has_pending(self, repo: str, pr_number: int) -> bool:
        """Check if a review request already exists in pending, done, or todo."""
        safe_repo = repo.replace("/", "-")
        pattern = f"{safe_repo}-{pr_number}-"
        return (
            any(f.name.startswith(pattern) for f in self._pending.glob("*.md"))
            or any(f.name.startswith(pattern) for f in self._done.glob("*.md"))
            or self.has_todo(repo, pr_number)
        )

    def has_todo(self, repo: str, pr_number: int) -> bool:
        """Check if a todo work document exists for this review."""
        safe_repo = repo.replace("/", "-")
        pattern = f"newjob-{safe_repo}-{pr_number}-"
        return any(f.name.startswith(pattern) for f in self._todo.glob("*.md"))

    def _list_folder(self, folder: Path) -> list[dict]:
        files = sorted(folder.glob("*.md"), key=lambda f: f.stat().st_mtime, reverse=True)
        return [
            {
                "filename": f.name,
                "path": str(f),
                "size": f.stat().st_size,
                "modified": f.stat().st_mtime,
            }
            for f in files
        ]
