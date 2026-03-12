"""MCP server for token-monitor — real-time token usage monitoring.

Wraps the token-monitor Go binary to provide token tracking tools
via MCP protocol. Designed for agent self-monitoring during sessions.
"""

import asyncio
import json
import logging
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from token_monitor_mcp.cli import (
    export_session,
    get_version,
    list_sessions,
    get_session_summary,
)

logger = logging.getLogger(__name__)

TOOLS: list[Tool] = [
    Tool(
        name="token_session_list",
        description="List all tracked Claude Code sessions with their token counts",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
    Tool(
        name="token_session_summary",
        description=(
            "Get token usage summary for a specific session. "
            "Returns total/input/output/cache tokens, cost, and duration."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "description": "Session name or UUID",
                },
            },
            "required": ["session"],
        },
    ),
    Tool(
        name="token_session_export",
        description=(
            "Export session data in agent-forge format. "
            "Output maps directly to Phase 4 session-log-schema tokens fields."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "description": "Session name or UUID",
                },
                "format": {
                    "type": "string",
                    "enum": ["agent-forge", "json", "csv"],
                    "description": "Export format (default: agent-forge)",
                },
            },
            "required": ["session"],
        },
    ),
    Tool(
        name="token_cost_check",
        description=(
            "Quick check of current session token cost in USD. "
            "Use at milestone boundaries to track spend."
        ),
        inputSchema={
            "type": "object",
            "properties": {
                "session": {
                    "type": "string",
                    "description": "Session name or UUID",
                },
            },
            "required": ["session"],
        },
    ),
    Tool(
        name="token_monitor_version",
        description="Get token-monitor binary version",
        inputSchema={
            "type": "object",
            "properties": {},
        },
    ),
]


def _handle_session_list() -> dict[str, Any]:
    """Handle token_session_list tool call."""
    sessions = list_sessions()
    return {"success": True, "data": {"sessions": sessions, "count": len(sessions)}}


def _handle_session_summary(session: str) -> dict[str, Any]:
    """Handle token_session_summary tool call."""
    summary = get_session_summary(session)
    return {
        "success": True,
        "data": {
            "session_id": summary.session_id,
            "project": summary.project,
            "date": summary.date,
            "tokens": {
                "total": summary.total,
                "input": summary.input,
                "output": summary.output,
                "cache_read": summary.cache_read,
                "cache_create": summary.cache_create,
            },
            "cost_usd": summary.cost_usd,
            "duration_minutes": summary.duration_minutes,
        },
    }


def _handle_session_export(session: str, fmt: str = "agent-forge") -> dict[str, Any]:
    """Handle token_session_export tool call."""
    raw = export_session(session, fmt)
    if fmt in ("agent-forge", "json"):
        return {"success": True, "data": json.loads(raw)}
    return {"success": True, "data": {"raw": raw}}


def _handle_cost_check(session: str) -> dict[str, Any]:
    """Handle token_cost_check tool call."""
    summary = get_session_summary(session)
    return {
        "success": True,
        "data": {
            "session_id": summary.session_id,
            "total_tokens": summary.total,
            "cost_usd": summary.cost_usd,
            "duration_minutes": summary.duration_minutes,
        },
    }


def _handle_version() -> dict[str, Any]:
    """Handle token_monitor_version tool call."""
    return {"success": True, "data": {"version": get_version()}}


_HANDLERS: dict[str, Any] = {
    "token_session_list": lambda **_: _handle_session_list(),
    "token_session_summary": lambda **kw: _handle_session_summary(kw["session"]),
    "token_session_export": lambda **kw: _handle_session_export(
        kw["session"], kw.get("format", "agent-forge")
    ),
    "token_cost_check": lambda **kw: _handle_cost_check(kw["session"]),
    "token_monitor_version": lambda **_: _handle_version(),
}


async def run_server() -> None:
    """Start the MCP server with stdio transport."""
    server = Server("token-monitor-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return TOOLS

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        handler = _HANDLERS.get(name)
        if not handler:
            result = {"success": False, "error": f"Unknown tool: {name}"}
            return [TextContent(type="text", text=json.dumps(result))]

        try:
            result = handler(**arguments)
            return [TextContent(type="text", text=json.dumps(result, ensure_ascii=False))]
        except Exception as exc:
            logger.exception("Tool %s failed", name)
            error_msg = str(exc)
            # Strip file paths and system details from error messages
            if "/" in error_msg:
                parts = error_msg.split(":")
                error_msg = parts[-1].strip() if parts else "internal error"
            result = {"success": False, "error": error_msg}
            return [TextContent(type="text", text=json.dumps(result))]

    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


def main() -> None:
    """CLI entry point."""
    logging.basicConfig(level=logging.INFO)
    asyncio.run(run_server())


if __name__ == "__main__":
    main()
