"""MCP server core — tool registration and protocol handling.

This is the single entry point for all tools. Each tool module
(gmail, github, etc.) registers its tools here at startup.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any, Protocol

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from shared.events import EventDispatcher, ReviewCompleted, ReviewDetected, BatchCycleFinished
from shared.hooks import TriggerFileHook
from shared.task.manager import TaskManager
from shared.task.store import FileTaskStore
from shared.types import TaskStatus, TaskType, ToolResult, ToolSource

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., ToolResult]


class Closeable(Protocol):
    """Protocol for objects with an async close method."""

    async def aclose(self) -> None: ...


class ToolServer:
    """MCP server that dynamically registers tools from modules.

    Tool modules call register_tool() to add their handlers.
    The server exposes them via MCP protocol (stdio transport).
    """

    def __init__(self) -> None:
        self._server = Server("agent-forge-tools")
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._clients: list[Closeable] = []
        self._task_manager = TaskManager(FileTaskStore())
        self._dispatcher = EventDispatcher()
        self._trigger_hook = TriggerFileHook()
        self._register_event_hooks()
        self._register_task_tools()
        self._setup_mcp_handlers()

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

    @property
    def dispatcher(self) -> EventDispatcher:
        return self._dispatcher

    def _register_event_hooks(self) -> None:
        """Subscribe trigger file hooks to lifecycle events."""
        self._dispatcher.subscribe(ReviewDetected, self._trigger_hook.on_review_detected)
        self._dispatcher.subscribe(ReviewCompleted, self._trigger_hook.on_review_completed)
        self._dispatcher.subscribe(BatchCycleFinished, self._trigger_hook.on_batch_cycle_finished)
        logger.info("Event hooks registered (%d subscribers)", self._dispatcher.subscriber_count)

    def track_client(self, client: Closeable) -> None:
        """Track an API client for cleanup on server shutdown."""
        self._clients.append(client)

    async def close_clients(self) -> None:
        """Close all tracked API clients, releasing connection pool resources."""
        for client in self._clients:
            try:
                await client.aclose()
            except Exception:
                logger.exception("Failed to close client: %s", type(client).__name__)
        self._clients.clear()

    def register_tool(
        self,
        name: str,
        description: str,
        input_schema: dict[str, Any],
        handler: ToolHandler,
    ) -> None:
        """Register an MCP tool with its handler function."""
        self._tools[name] = Tool(
            name=name,
            description=description,
            inputSchema=input_schema,
        )
        self._handlers[name] = handler
        logger.info("Registered tool: %s", name)

    def _register_task_tools(self) -> None:
        """Register built-in task management tools."""
        self.register_tool(
            name="task_list",
            description="List tasks with optional filters by source, status, and type",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": [s.value for s in ToolSource],
                        "description": "Filter by source",
                    },
                    "status": {
                        "type": "string",
                        "enum": [s.value for s in TaskStatus],
                        "description": "Filter by status",
                    },
                    "type": {
                        "type": "string",
                        "enum": [t.value for t in TaskType],
                        "description": "Filter by task type",
                    },
                },
            },
            handler=self._handle_task_list,
        )

        self.register_tool(
            name="task_sync",
            description="Sync tasks from an external source (GitHub issues/PRs or Gmail)",
            input_schema={
                "type": "object",
                "properties": {
                    "source": {
                        "type": "string",
                        "enum": [s.value for s in ToolSource],
                        "description": "Source to sync from",
                    },
                    "repo": {
                        "type": "string",
                        "description": "Repository (for GitHub) or query (for Gmail)",
                    },
                },
                "required": ["source"],
            },
            handler=self._handle_task_sync,
        )

        self.register_tool(
            name="task_update",
            description="Update the status of a task",
            input_schema={
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "Task ID to update"},
                    "status": {
                        "type": "string",
                        "enum": [s.value for s in TaskStatus],
                        "description": "New status",
                    },
                },
                "required": ["task_id", "status"],
            },
            handler=self._handle_task_update,
        )

    def _register_external_tools(self) -> None:
        """Register Gmail and GitHub tool modules."""
        try:
            from gmail.tools import register as register_gmail

            register_gmail(self)
        except ImportError:
            logger.warning("Gmail tools not available")

        try:
            from github.tools import register as register_github
            from github.tools import register_actions

            register_github(self)
            register_actions(self)
        except ImportError:
            logger.warning("GitHub tools not available")

        try:
            from github.review.tools import register as register_review

            register_review(self, dispatcher=self._dispatcher)
        except ImportError:
            logger.warning("Review tools not available")

    def _setup_mcp_handlers(self) -> None:
        """Wire MCP protocol handlers to the server."""

        @self._server.list_tools()
        async def list_tools() -> list[Tool]:
            return list(self._tools.values())

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            handler = self._handlers.get(name)
            if not handler:
                logger.warning("Unknown tool requested: %s", name)
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            logger.info("Tool call: %s args=%s", name, list(arguments.keys()))
            try:
                result = handler(**arguments)
                if inspect.isawaitable(result):
                    result = await result
                logger.info("Tool result: %s success=%s", name, result.success)
                logger.debug("Tool result detail: %s data_keys=%s", name,
                             list(result.data.keys()) if isinstance(result.data, dict) else type(result.data).__name__)
                return [TextContent(type="text", text=result.model_dump_json())]
            except Exception as exc:
                logger.exception("Tool %s failed", name)
                from shared.sanitize import sanitize
                error_result = ToolResult(success=False, error=sanitize(str(exc)))
                return [TextContent(type="text", text=error_result.model_dump_json())]

    def _handle_task_list(self, **kwargs: Any) -> ToolResult:
        source = ToolSource(kwargs["source"]) if kwargs.get("source") else None
        status = TaskStatus(kwargs["status"]) if kwargs.get("status") else None
        task_type = TaskType(kwargs["type"]) if kwargs.get("type") else None
        return self._task_manager.list_tasks(source=source, status=status, task_type=task_type)

    def _handle_task_sync(self, **kwargs: Any) -> ToolResult:
        source_str = kwargs.get("source", "")
        repo = kwargs.get("repo", "")
        if not source_str:
            return ToolResult(success=False, error="source is required")

        return ToolResult(
            success=True,
            data={
                "message": f"Use monitors to sync {source_str} tasks",
                "hint": f"Call github_list_issues or gmail_list_messages with repo={repo}",
            },
        )

    def _handle_task_update(self, **kwargs: Any) -> ToolResult:
        return self._task_manager.update_status(
            task_id=kwargs["task_id"],
            status=TaskStatus(kwargs["status"]),
        )


_server_instance: ToolServer | None = None


def get_server() -> ToolServer:
    """Get or create the singleton ToolServer instance."""
    global _server_instance
    if _server_instance is None:
        _server_instance = ToolServer()
        _server_instance._register_external_tools()
    return _server_instance


async def run_server() -> None:
    """Start the MCP server with stdio transport and batch scheduler."""
    server = get_server()
    scheduler = _create_batch_scheduler(server)

    try:
        if scheduler:
            await scheduler.start()

        async with stdio_server() as (read_stream, write_stream):
            await server._server.run(
                read_stream, write_stream, server._server.create_initialization_options()
            )
    finally:
        if scheduler:
            await scheduler.stop()
        await server.close_clients()


def _create_batch_scheduler(server: ToolServer):
    """Create and configure the batch scheduler with available watchers."""
    try:
        from shared.batch.scheduler import BatchScheduler

        scheduler = BatchScheduler(dispatcher=server.dispatcher)
        _register_watchers(scheduler, server)

        if not scheduler._watchers:
            return None
        return scheduler
    except ImportError:
        logger.warning("Batch scheduler not available")
        return None


def _register_watchers(scheduler, server: ToolServer) -> None:
    """Register all available watchers with the scheduler."""
    try:
        from github.review.watcher import GitHubReviewWatcher
        from github.review.store import ReviewStore
        from gmail.client import GmailClient
        from github.client import GitHubClient
        from shared.auth.credentials import load_gmail_config, load_github_config
        from shared.auth.token_store import TokenStore

        token_store = TokenStore()

        gmail_config = load_gmail_config()
        gmail_token = token_store.load(gmail_config.service)
        github_config = load_github_config()
        github_token_str = github_config.api_key.get_secret_value()

        if not gmail_token:
            logger.warning("Review watcher skipped: Gmail token not found. Run agent-forge-setup.")
            return
        if not github_token_str:
            logger.warning("Review watcher skipped: GITHUB_TOKEN not set.")
            return

        gmail_client = GmailClient(token=gmail_token.access_token)
        github_client = GitHubClient(token=github_token_str)
        server.track_client(gmail_client)
        server.track_client(github_client)

        watcher = GitHubReviewWatcher(
            gmail_client=gmail_client,
            github_client=github_client,
            store=ReviewStore(),
            dispatcher=server.dispatcher,
        )
        scheduler.register(watcher)
        logger.info("Review watcher registered successfully")
    except ImportError as exc:
        logger.warning("Review watcher not available (missing dependency): %s", exc)
    except Exception:
        logger.exception("Failed to register review watcher")


def main() -> None:
    """CLI entry point."""
    from dotenv import load_dotenv
    from shared.logging import setup_logging
    load_dotenv()
    setup_logging()
    logger.info("workspace-mcp server starting")
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
