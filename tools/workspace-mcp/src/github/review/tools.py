"""MCP tools for review request management.

Provides tools to check for new review requests and generate
agent-friendly todo documents.
"""

import logging
from typing import Any

from github.review.models import ReviewRequest
from github.review.store import ReviewStore
from shared.server import ToolServer
from shared.types import ToolResult

logger = logging.getLogger(__name__)


def register(server: ToolServer) -> None:
    """Register review management MCP tools."""
    store = ReviewStore()

    server.register_tool(
        name="review_list_pending",
        description="List pending code review requests that need attention",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=_make_list_handler(store, "pending"),
    )

    server.register_tool(
        name="review_list_done",
        description="List completed code reviews",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=_make_list_handler(store, "done"),
    )

    server.register_tool(
        name="review_list_todo",
        description="List agent todo documents for code reviews",
        input_schema={
            "type": "object",
            "properties": {},
        },
        handler=_make_list_handler(store, "todo"),
    )

    server.register_tool(
        name="review_create_todo",
        description=(
            "Create an agent-friendly todo document from a pending review request. "
            "Reads the pending review file and generates a work plan in the todo folder."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename of the pending review (e.g. 'owner-repo-123-20260317.md')",
                },
            },
            "required": ["filename"],
        },
        handler=_make_create_todo_handler(store),
    )

    server.register_tool(
        name="review_read_todo",
        description=(
            "Read the full content of a todo document. "
            "Returns the markdown content with repo, PR info, and setup commands."
        ),
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename of the todo document (e.g. 'newjob-owner-repo-123-20260317.md')",
                },
            },
            "required": ["filename"],
        },
        handler=_make_read_handler(store, "todo"),
    )

    server.register_tool(
        name="review_update_todo",
        description="Append review result to a todo document",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename of the todo document",
                },
                "result": {
                    "type": "string",
                    "description": "Review result markdown to append",
                },
            },
            "required": ["filename", "result"],
        },
        handler=_make_update_todo_handler(store),
    )

    server.register_tool(
        name="review_mark_done",
        description="Mark a review as completed (moves from pending to done)",
        input_schema={
            "type": "object",
            "properties": {
                "filename": {
                    "type": "string",
                    "description": "Filename of the pending review to mark as done",
                },
            },
            "required": ["filename"],
        },
        handler=_make_mark_done_handler(store),
    )


def _make_list_handler(store: ReviewStore, folder: str) -> Any:
    def handler(**kwargs: Any) -> ToolResult:
        if folder == "pending":
            items = store.list_pending()
        elif folder == "done":
            items = store.list_done()
        else:
            items = store.list_todo()
        return ToolResult(success=True, data={"items": items, "count": len(items)})

    return handler


def _make_read_handler(store: ReviewStore, folder: str) -> Any:
    def handler(*, filename: str, **kwargs: Any) -> ToolResult:
        folder_path = getattr(store, f"_{folder}")
        file_path = folder_path / filename
        if not file_path.exists():
            return ToolResult(success=False, error=f"File not found: {filename}")
        content = file_path.read_text(encoding="utf-8")
        return ToolResult(success=True, data={"filename": filename, "content": content})

    return handler


def _make_update_todo_handler(store: ReviewStore) -> Any:
    def handler(*, filename: str, result: str, **kwargs: Any) -> ToolResult:
        file_path = store._todo / filename
        if not file_path.exists():
            return ToolResult(success=False, error=f"Todo not found: {filename}")

        existing = file_path.read_text(encoding="utf-8")
        updated = existing + "\n---\n\n" + result + "\n"
        file_path.write_text(updated, encoding="utf-8")

        return ToolResult(success=True, data={"message": f"Updated: {filename}"})

    return handler


def _make_create_todo_handler(store: ReviewStore) -> Any:
    def handler(*, filename: str, **kwargs: Any) -> ToolResult:
        pending_path = store._pending / filename
        if not pending_path.exists():
            return ToolResult(success=False, error=f"Pending review not found: {filename}")

        slug = filename.removesuffix(".md")
        content = pending_path.read_text(encoding="utf-8")

        repo, pr_number = _parse_slug(slug)
        if not repo:
            return ToolResult(success=False, error=f"Cannot parse review info from: {filename}")

        review = _rebuild_review_from_markdown(content, repo, pr_number)
        todo_path = store.save_todo(review)

        return ToolResult(
            success=True,
            data={
                "todo_file": str(todo_path),
                "filename": todo_path.name,
                "repo": repo,
                "pr_number": pr_number,
            },
        )

    return handler


def _make_mark_done_handler(store: ReviewStore) -> Any:
    def handler(*, filename: str, **kwargs: Any) -> ToolResult:
        slug = filename.removesuffix(".md")
        if store.mark_done(slug):
            return ToolResult(success=True, data={"message": f"Marked as done: {filename}"})
        return ToolResult(success=False, error=f"Pending review not found: {filename}")

    return handler


def _parse_slug(slug: str) -> tuple[str, int]:
    """Parse 'owner-repo-123-20260317' into ('owner/repo', 123)."""
    parts = slug.split("-")
    if len(parts) < 4:
        return ("", 0)
    try:
        date_part = parts[-1]
        pr_part = parts[-2]
        pr_number = int(pr_part)
        repo_parts = parts[:-2]
        if len(repo_parts) >= 2:
            owner = repo_parts[0]
            repo_name = "-".join(repo_parts[1:])
            return (f"{owner}/{repo_name}", pr_number)
    except (ValueError, IndexError):
        pass
    return ("", 0)


def _rebuild_review_from_markdown(content: str, repo: str, pr_number: int) -> ReviewRequest:
    """Rebuild a ReviewRequest from the pending markdown content."""
    import re

    title = ""
    url = ""
    requester = ""
    head_branch = ""
    base_branch = ""

    for line in content.split("\n"):
        if "| Title |" in line:
            match = re.search(r"\|\s*(.+?)\s*\|$", line)
            if match:
                title = match.group(1).strip()
        elif "| URL |" in line:
            match = re.search(r"\|\s*(.+?)\s*\|$", line)
            if match:
                url = match.group(1).strip()
        elif "| Requester |" in line:
            match = re.search(r"\|\s*(.+?)\s*\|$", line)
            if match:
                requester = match.group(1).strip()
        elif "| Branch |" in line:
            match = re.search(r"`(.+?)`\s*->\s*`(.+?)`", line)
            if match:
                head_branch = match.group(1)
                base_branch = match.group(2)

    return ReviewRequest(
        repo=repo,
        pr_number=pr_number,
        pr_title=title,
        pr_url=url,
        requester=requester,
        head_branch=head_branch,
        base_branch=base_branch,
    )
