"""Tests for Gmail API client — RED phase.

Gmail client wraps the Google Gmail API and returns sanitized data
(no auth tokens, no raw headers beyond what's needed).
"""

from unittest.mock import AsyncMock, patch

import pytest

from shared.auth.token_store import StoredToken


class TestGmailClient:
    """Gmail client should provide read-only access to Gmail."""

    @pytest.fixture
    def client(self, gmail_token):
        from gmail.client import GmailClient

        return GmailClient(token=gmail_token)

    @pytest.mark.asyncio
    async def test_list_messages_returns_simplified_list(
        self, client, sample_gmail_messages, sample_gmail_message_detail
    ):
        """list_messages should return subject, sender, date — not raw API response."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                sample_gmail_messages,
                sample_gmail_message_detail,
                {**sample_gmail_message_detail, "id": "msg-002",
                 "payload": {**sample_gmail_message_detail["payload"],
                             "headers": [
                                 {"name": "From", "value": "carol@example.com"},
                                 {"name": "Subject", "value": "Lunch?"},
                                 {"name": "Date", "value": "Wed, 11 Mar 2026 11:00:00 +0900"},
                             ]}},
                {**sample_gmail_message_detail, "id": "msg-003",
                 "payload": {**sample_gmail_message_detail["payload"],
                             "headers": [
                                 {"name": "From", "value": "dave@example.com"},
                                 {"name": "Subject", "value": "PR Review"},
                                 {"name": "Date", "value": "Wed, 11 Mar 2026 12:00:00 +0900"},
                             ]}},
            ]

            messages = await client.list_messages(max_results=3)

        assert len(messages) == 3
        first = messages[0]
        assert first["id"] == "msg-001"
        assert first["subject"] == "Team Meeting"
        assert first["sender"] == "alice@example.com"
        assert "date" in first

    @pytest.mark.asyncio
    async def test_list_messages_with_query(self, client, sample_gmail_messages, sample_gmail_message_detail):
        """list_messages should pass query parameter to Gmail API."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                {"messages": [{"id": "msg-001", "threadId": "t1"}], "resultSizeEstimate": 1},
                sample_gmail_message_detail,
            ]

            await client.list_messages(query="from:alice@example.com", max_results=5)

        first_call_args = mock_req.call_args_list[0]
        assert "from:alice@example.com" in str(first_call_args)

    @pytest.mark.asyncio
    async def test_list_messages_empty(self, client):
        """list_messages returns empty list when no messages match."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = {"messages": [], "resultSizeEstimate": 0}

            messages = await client.list_messages()

        assert messages == []

    @pytest.mark.asyncio
    async def test_read_message_returns_body_and_metadata(
        self, client, sample_gmail_message_detail
    ):
        """read_message should return decoded body text and metadata."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = sample_gmail_message_detail

            result = await client.read_message("msg-001")

        assert result["id"] == "msg-001"
        assert result["subject"] == "Team Meeting"
        assert result["sender"] == "alice@example.com"
        assert "body" in result
        assert "meeting" in result["body"].lower()

    @pytest.mark.asyncio
    async def test_read_message_multipart(self, client):
        """read_message should handle multipart messages (HTML + plain text)."""
        multipart_msg = {
            "id": "msg-multi",
            "threadId": "t1",
            "payload": {
                "mimeType": "multipart/alternative",
                "headers": [
                    {"name": "From", "value": "test@example.com"},
                    {"name": "Subject", "value": "Multipart"},
                    {"name": "Date", "value": "Wed, 11 Mar 2026 10:00:00 +0900"},
                ],
                "parts": [
                    {
                        "mimeType": "text/plain",
                        "body": {
                            "data": "UGxhaW4gdGV4dCBib2R5",
                        },
                    },
                    {
                        "mimeType": "text/html",
                        "body": {
                            "data": "PGh0bWw+Qm9keTwvaHRtbD4=",
                        },
                    },
                ],
            },
        }
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = multipart_msg

            result = await client.read_message("msg-multi")

        assert result["body"] == "Plain text body"

    @pytest.mark.asyncio
    async def test_search_messages(self, client, sample_gmail_messages, sample_gmail_message_detail):
        """search should be equivalent to list_messages with a query."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.side_effect = [
                {"messages": [{"id": "msg-001", "threadId": "t1"}], "resultSizeEstimate": 1},
                sample_gmail_message_detail,
            ]

            results = await client.search("subject:meeting")

        assert len(results) == 1
        assert results[0]["subject"] == "Team Meeting"

    @pytest.mark.asyncio
    async def test_no_token_in_response(self, client, sample_gmail_message_detail):
        """Responses must NEVER contain auth tokens."""
        with patch.object(client, "_request", new_callable=AsyncMock) as mock_req:
            mock_req.return_value = sample_gmail_message_detail

            result = await client.read_message("msg-001")

        result_str = str(result)
        assert "ya29." not in result_str
        assert "access_token" not in result_str
        assert "refresh_token" not in result_str
        assert "Bearer" not in result_str

    @pytest.mark.asyncio
    async def test_request_uses_auth_header(self, client):
        """Internal _request should send Authorization header (but never return it)."""
        assert client._auth_header == "Bearer ya29.test-access-token"

    @pytest.mark.asyncio
    async def test_aclose_releases_http_client(self, client):
        """aclose() should close the underlying httpx.AsyncClient."""
        with patch.object(client._http, "aclose", new_callable=AsyncMock) as mock_close:
            await client.aclose()
            mock_close.assert_called_once()
