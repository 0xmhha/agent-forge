"""Gmail MCP tool registration and handlers.

Each handler wraps GmailClient methods and returns ToolResult.
Token sanitization happens at two layers:
1. GmailClient never includes tokens in its return values
2. Handlers scrub any accidental token leaks from error messages
"""

import re
from typing import Any

from gmail.client import GmailClient
from shared.server import ToolServer
from shared.types import ToolResult

_TOKEN_PATTERN = re.compile(r"ya29\.[A-Za-z0-9_-]+|Bearer\s+\S+|token\s+\S+", re.IGNORECASE)


def register(server: ToolServer) -> None:
    """Register all Gmail MCP tools with the server."""
    server.register_tool(
        name="gmail_list_messages",
        description="List recent emails with optional search query",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query (e.g. 'from:alice@example.com')",
                    "default": "",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum number of messages to return",
                    "default": 10,
                    "minimum": 1,
                    "maximum": 50,
                },
            },
        },
        handler=_make_list_handler(server),
    )

    server.register_tool(
        name="gmail_read_message",
        description="Read a specific email message by ID",
        input_schema={
            "type": "object",
            "properties": {
                "message_id": {
                    "type": "string",
                    "description": "Gmail message ID",
                },
            },
            "required": ["message_id"],
        },
        handler=_make_read_handler(server),
    )

    server.register_tool(
        name="gmail_search",
        description="Search emails using Gmail query syntax",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Gmail search query",
                },
                "max_results": {
                    "type": "integer",
                    "description": "Maximum results",
                    "default": 10,
                },
            },
            "required": ["query"],
        },
        handler=_make_search_handler(server),
    )


async def handle_list_messages(
    *,
    client: GmailClient,
    max_results: int = 10,
    query: str = "",
) -> ToolResult:
    """Handle gmail_list_messages tool call."""
    try:
        messages = await client.list_messages(query=query, max_results=max_results)
        return ToolResult(
            success=True,
            data={"messages": messages, "count": len(messages)},
        )
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_read_message(
    *,
    client: GmailClient,
    message_id: str,
) -> ToolResult:
    """Handle gmail_read_message tool call."""
    try:
        message = await client.read_message(message_id)
        return ToolResult(
            success=True,
            data={"message": message},
        )
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


async def handle_search(
    *,
    client: GmailClient,
    query: str,
    max_results: int = 10,
) -> ToolResult:
    """Handle gmail_search tool call."""
    try:
        results = await client.search(query=query, max_results=max_results)
        return ToolResult(
            success=True,
            data={"messages": results, "count": len(results)},
        )
    except Exception as exc:
        return ToolResult(success=False, error=_sanitize_error(str(exc)))


def _sanitize_error(message: str) -> str:
    """Remove any accidentally leaked tokens from error messages."""
    return _TOKEN_PATTERN.sub("[REDACTED]", message)


def _make_list_handler(server: ToolServer) -> Any:
    """Create a bound handler for gmail_list_messages."""

    def handler(**kwargs: Any) -> ToolResult:
        raise NotImplementedError("Gmail client not configured — run OAuth flow first")

    return handler


def _make_read_handler(server: ToolServer) -> Any:
    """Create a bound handler for gmail_read_message."""

    def handler(**kwargs: Any) -> ToolResult:
        raise NotImplementedError("Gmail client not configured — run OAuth flow first")

    return handler


def _make_search_handler(server: ToolServer) -> Any:
    """Create a bound handler for gmail_search."""

    def handler(**kwargs: Any) -> ToolResult:
        raise NotImplementedError("Gmail client not configured — run OAuth flow first")

    return handler
