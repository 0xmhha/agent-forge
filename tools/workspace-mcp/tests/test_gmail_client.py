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


class TestGmailClientTokenRefresh:
    """Token provider should refresh the Authorization header mid-session."""

    @pytest.fixture
    def token_provider(self):
        return AsyncMock(return_value="ya29.new-refreshed-token")

    @pytest.fixture
    def client_with_provider(self, gmail_token, token_provider):
        from gmail.client import GmailClient

        return GmailClient(token=gmail_token, token_provider=token_provider)

    @pytest.mark.asyncio
    async def test_refreshes_header_before_request(self, client_with_provider, token_provider):
        """_request should call token_provider and update Authorization header."""
        with patch.object(
            client_with_provider._http, "request", new_callable=AsyncMock
        ) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {"messages": []}
            mock_response.raise_for_status = lambda: None
            mock_http.return_value = mock_response

            await client_with_provider._request("GET", "https://example.com")

        token_provider.assert_called_once()
        assert client_with_provider._auth_header == "Bearer ya29.new-refreshed-token"

    @pytest.mark.asyncio
    async def test_keeps_cached_header_when_provider_returns_none(self, gmail_token):
        """If token_provider returns None, keep the existing header."""
        from gmail.client import GmailClient

        provider = AsyncMock(return_value=None)
        client = GmailClient(token=gmail_token, token_provider=provider)
        original_header = client._auth_header

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status = lambda: None
            mock_http.return_value = mock_response

            await client._request("GET", "https://example.com")

        assert client._auth_header == original_header

    @pytest.mark.asyncio
    async def test_no_provider_skips_refresh(self):
        """Without token_provider, _ensure_fresh_token is a no-op."""
        from gmail.client import GmailClient

        client_no_provider = GmailClient(token="static-token")
        original_header = client_no_provider._auth_header

        with patch.object(
            client_no_provider._http, "request", new_callable=AsyncMock
        ) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status = lambda: None
            mock_http.return_value = mock_response

            await client_no_provider._request("GET", "https://example.com")

        assert client_no_provider._auth_header == original_header

    @pytest.mark.asyncio
    async def test_header_only_updates_when_token_changes(self, gmail_token):
        """If provider returns same token, header shouldn't be reassigned."""
        from gmail.client import GmailClient

        provider = AsyncMock(return_value="ya29.test-access-token")
        client = GmailClient(token=gmail_token, token_provider=provider)

        with patch.object(client._http, "request", new_callable=AsyncMock) as mock_http:
            mock_response = AsyncMock()
            mock_response.status_code = 200
            mock_response.json.return_value = {}
            mock_response.raise_for_status = lambda: None
            mock_http.return_value = mock_response

            await client._request("GET", "https://example.com")

        # Same token — header value unchanged
        assert client._auth_header == "Bearer ya29.test-access-token"
