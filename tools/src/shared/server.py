"""MCP server core — tool registration and protocol handling.

This is the single entry point for all tools. Each tool module
(gmail, github, etc.) registers its tools here at startup.
"""

import asyncio
import inspect
import logging
from collections.abc import Callable
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from shared.task.manager import TaskManager
from shared.task.store import FileTaskStore
from shared.types import TaskStatus, TaskType, ToolResult, ToolSource

logger = logging.getLogger(__name__)

ToolHandler = Callable[..., ToolResult]


class ToolServer:
    """MCP server that dynamically registers tools from modules.

    Tool modules call register_tool() to add their handlers.
    The server exposes them via MCP protocol (stdio transport).
    """

    def __init__(self) -> None:
        self._server = Server("agent-forge-tools")
        self._tools: dict[str, Tool] = {}
        self._handlers: dict[str, ToolHandler] = {}
        self._task_manager = TaskManager(FileTaskStore())
        self._register_task_tools()
        self._setup_mcp_handlers()

    @property
    def task_manager(self) -> TaskManager:
        return self._task_manager

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

    def _setup_mcp_handlers(self) -> None:
        """Wire MCP protocol handlers to the server."""

        @self._server.list_tools()
        async def list_tools() -> list[Tool]:
            return list(self._tools.values())

        @self._server.call_tool()
        async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
            handler = self._handlers.get(name)
            if not handler:
                return [TextContent(type="text", text=f"Unknown tool: {name}")]

            try:
                result = handler(**arguments)
                if inspect.isawaitable(result):
                    result = await result
                return [TextContent(type="text", text=result.model_dump_json())]
            except Exception as exc:
                logger.exception("Tool %s failed", name)
                error_result = ToolResult(success=False, error=str(exc))
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
    """Start the MCP server with stdio transport."""
    server = get_server()
    async with stdio_server() as (read_stream, write_stream):
        await server._server.run(
            read_stream, write_stream, server._server.create_initialization_options()
        )


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
