"""Gmail API client — read-only access, tokens never exposed in responses."""

import base64
from typing import Any

import httpx

from shared.auth.token_store import StoredToken

_GMAIL_API = "https://gmail.googleapis.com/gmail/v1/users/me"

_HEADER_FIELDS = {"From", "To", "Subject", "Date"}


class GmailClient:
    """Wraps the Gmail REST API with read-only operations.

    Auth header is stored internally and never included in return values.
    All public methods return sanitized dicts (no tokens, no raw headers).
    """

    def __init__(self, token: str | StoredToken) -> None:
        if isinstance(token, str):
            self._auth_header = f"Bearer {token}"
        else:
            self._auth_header = f"{token.token_type} {token.access_token}"
        self._http = httpx.AsyncClient(
            headers={"Authorization": self._auth_header, "Accept": "application/json"},
        )

    async def list_messages(
        self,
        query: str = "",
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """List messages with optional query filter. Returns simplified metadata."""
        params: dict[str, Any] = {"maxResults": max_results}
        if query:
            params["q"] = query

        data = await self._request("GET", f"{_GMAIL_API}/messages", params=params)
        raw_messages = data.get("messages", [])
        if not raw_messages:
            return []

        results = []
        for msg_ref in raw_messages:
            detail = await self._request("GET", f"{_GMAIL_API}/messages/{msg_ref['id']}")
            results.append(_extract_metadata(detail))

        return results

    async def read_message(self, message_id: str) -> dict[str, Any]:
        """Read a single message with decoded body text."""
        data = await self._request("GET", f"{_GMAIL_API}/messages/{message_id}")
        metadata = _extract_metadata(data)
        metadata["body"] = _extract_body(data.get("payload", {}))
        return metadata

    async def search(
        self,
        query: str,
        max_results: int = 10,
    ) -> list[dict[str, Any]]:
        """Search messages by Gmail query syntax."""
        return await self.list_messages(query=query, max_results=max_results)

    async def aclose(self) -> None:
        """Close the underlying HTTP client and release connection pool resources."""
        await self._http.aclose()

    async def _request(
        self,
        method: str,
        url: str,
        *,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send authenticated request to Gmail API."""
        response = await self._http.request(method, url, params=params)
        response.raise_for_status()
        return response.json()


def _extract_metadata(message: dict[str, Any]) -> dict[str, Any]:
    """Extract simplified metadata from a raw Gmail message."""
    headers = {}
    for header in message.get("payload", {}).get("headers", []):
        name = header.get("name", "")
        if name in _HEADER_FIELDS:
            headers[name] = header.get("value", "")

    return {
        "id": message.get("id", ""),
        "thread_id": message.get("threadId", ""),
        "subject": headers.get("Subject", ""),
        "sender": headers.get("From", ""),
        "to": headers.get("To", ""),
        "date": headers.get("Date", ""),
        "snippet": message.get("snippet", ""),
    }


def _extract_body(payload: dict[str, Any]) -> str:
    """Decode message body, preferring plain text over HTML for multipart."""
    mime_type = payload.get("mimeType", "")

    if mime_type.startswith("multipart/"):
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                return _decode_body_data(part.get("body", {}))
        for part in payload.get("parts", []):
            body = _extract_body(part)
            if body:
                return body
        return ""

    body_data = payload.get("body", {})
    return _decode_body_data(body_data)


def _decode_body_data(body: dict[str, Any]) -> str:
    """Base64url-decode the body data field."""
    data = body.get("data", "")
    if not data:
        return ""
    padded = data + "=" * (4 - len(data) % 4)
    return base64.urlsafe_b64decode(padded).decode("utf-8", errors="replace")
