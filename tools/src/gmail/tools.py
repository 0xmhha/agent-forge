"""Gmail MCP tool registration and handlers.

Each handler wraps GmailClient methods and returns ToolResult.
Token sanitization uses the shared sanitize module as a defense layer
against accidental token leaks in error messages.
"""

import logging
from typing import Any

from gmail.client import GmailClient
from shared.sanitize import sanitize
from shared.server import ToolServer
from shared.types import ToolResult

logger = logging.getLogger(__name__)


def register(server: ToolServer) -> None:
    """Register all Gmail MCP tools with the server.

    Creates a GmailClient from stored OAuth token if available.
    Tools return clear error messages when credentials are missing.
    """
    client = _create_client(server)

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
        handler=_make_handler(client, _handle_list_messages),
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
        handler=_make_handler(client, _handle_read_message),
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
        handler=_make_handler(client, _handle_search),
    )


def _create_client(server: ToolServer) -> GmailClient | None:
    """Create GmailClient from stored OAuth token, or None if unavailable."""
    try:
        from shared.auth.credentials import load_gmail_config
        from shared.auth.oauth_flow import OAuthFlow
        from shared.auth.token_store import TokenStore

        config = load_gmail_config()
        token_store = TokenStore()
        token = token_store.load(config.service)

        if token is None:
            logger.warning("Gmail: no stored token — tools will return auth-required error")
            return None

        return GmailClient(token=token.access_token)
    except Exception:
        logger.exception("Gmail client initialization failed")
        return None


def _make_handler(client: GmailClient | None, handler_fn: Any) -> Any:
    """Wrap an async handler with client injection and error handling."""

    async def handler(**kwargs: Any) -> ToolResult:
        if client is None:
            return ToolResult(
                success=False,
                error="Gmail not configured — run OAuth authorization first",
            )
        try:
            return await handler_fn(client=client, **kwargs)
        except Exception as exc:
            return ToolResult(success=False, error=sanitize(str(exc)))

    return handler


async def _handle_list_messages(
    *,
    client: GmailClient,
    max_results: int = 10,
    query: str = "",
) -> ToolResult:
    """Handle gmail_list_messages tool call."""
    messages = await client.list_messages(query=query, max_results=max_results)
    return ToolResult(
        success=True,
        data={"messages": messages, "count": len(messages)},
    )


async def _handle_read_message(
    *,
    client: GmailClient,
    message_id: str,
) -> ToolResult:
    """Handle gmail_read_message tool call."""
    message = await client.read_message(message_id)
    return ToolResult(success=True, data={"message": message})


async def _handle_search(
    *,
    client: GmailClient,
    query: str,
    max_results: int = 10,
) -> ToolResult:
    """Handle gmail_search tool call."""
    results = await client.search(query=query, max_results=max_results)
    return ToolResult(
        success=True,
        data={"messages": results, "count": len(results)},
    )
