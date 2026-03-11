"""Tests for Gmail MCP tool registration — RED phase.

Tools are the MCP interface layer. They call GmailClient methods
and return ToolResult objects.
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from shared.types import ToolResult


class TestGmailToolRegistration:
    """Gmail tools should register correctly with the MCP server."""

    def test_register_adds_three_tools(self):
        """Gmail module should register exactly 3 tools."""
        from gmail.tools import register

        mock_server = MagicMock()
        register(mock_server)

        assert mock_server.register_tool.call_count == 3
        tool_names = [call.kwargs["name"] for call in mock_server.register_tool.call_args_list]
        assert "gmail_list_messages" in tool_names
        assert "gmail_read_message" in tool_names
        assert "gmail_search" in tool_names

    def test_tool_schemas_have_required_fields(self):
        """Each tool schema should define proper input parameters."""
        from gmail.tools import register

        mock_server = MagicMock()
        register(mock_server)

        schemas = {
            call.kwargs["name"]: call.kwargs["input_schema"]
            for call in mock_server.register_tool.call_args_list
        }

        list_schema = schemas["gmail_list_messages"]
        assert "max_results" in list_schema["properties"]

        read_schema = schemas["gmail_read_message"]
        assert "message_id" in read_schema["properties"]
        assert "message_id" in read_schema["required"]

        search_schema = schemas["gmail_search"]
        assert "query" in search_schema["properties"]
        assert "query" in search_schema["required"]


class TestGmailToolHandlers:
    """Gmail tool handlers should return ToolResult with sanitized data."""

    @pytest.mark.asyncio
    async def test_handle_list_messages(self):
        """gmail_list_messages handler should return message list."""
        from gmail.tools import handle_list_messages

        mock_client = AsyncMock()
        mock_client.list_messages.return_value = [
            {"id": "msg-001", "subject": "Hello", "sender": "a@b.com", "date": "2026-03-11"},
        ]

        result = await handle_list_messages(
            client=mock_client, max_results=10, query=""
        )

        assert isinstance(result, ToolResult)
        assert result.success is True
        assert len(result.data["messages"]) == 1
        assert result.data["messages"][0]["subject"] == "Hello"

    @pytest.mark.asyncio
    async def test_handle_read_message(self):
        """gmail_read_message handler should return message detail."""
        from gmail.tools import handle_read_message

        mock_client = AsyncMock()
        mock_client.read_message.return_value = {
            "id": "msg-001",
            "subject": "Hello",
            "sender": "a@b.com",
            "body": "Message body here",
        }

        result = await handle_read_message(client=mock_client, message_id="msg-001")

        assert result.success is True
        assert result.data["message"]["body"] == "Message body here"

    @pytest.mark.asyncio
    async def test_handle_search(self):
        """gmail_search handler should return search results."""
        from gmail.tools import handle_search

        mock_client = AsyncMock()
        mock_client.search.return_value = [
            {"id": "msg-001", "subject": "Meeting", "sender": "a@b.com", "date": "2026-03-11"},
        ]

        result = await handle_search(client=mock_client, query="subject:meeting")

        assert result.success is True
        assert result.data["count"] == 1

    @pytest.mark.asyncio
    async def test_handler_error_returns_failure(self):
        """Handlers should catch exceptions and return ToolResult with error."""
        from gmail.tools import handle_list_messages

        mock_client = AsyncMock()
        mock_client.list_messages.side_effect = Exception("API quota exceeded")

        result = await handle_list_messages(client=mock_client, max_results=10, query="")

        assert result.success is False
        assert "quota" in result.error.lower()

    @pytest.mark.asyncio
    async def test_no_token_leak_in_error(self):
        """Even error messages must not contain token information."""
        from gmail.tools import handle_list_messages

        mock_client = AsyncMock()
        mock_client.list_messages.side_effect = Exception(
            "Request failed with token ya29.secret123"
        )

        result = await handle_list_messages(client=mock_client, max_results=10, query="")

        assert result.success is False
        assert "ya29." not in result.error
        assert "secret" not in result.error
