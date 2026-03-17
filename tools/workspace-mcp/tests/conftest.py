"""Shared fixtures for tool platform tests."""

import tempfile
from pathlib import Path
from unittest.mock import AsyncMock

import pytest

from shared.auth.token_store import StoredToken, TokenStore
from shared.task.store import FileTaskStore


@pytest.fixture
def tmp_dir():
    with tempfile.TemporaryDirectory() as td:
        yield Path(td)


@pytest.fixture
def token_store(tmp_dir):
    return TokenStore(store_dir=tmp_dir / "tokens")


@pytest.fixture
def task_store(tmp_dir):
    return FileTaskStore(store_dir=tmp_dir / "tasks")


@pytest.fixture(autouse=True)
def _reset_github_shared_client():
    """Reset global _shared_client between tests to prevent state leakage."""
    import github.tools as gt

    gt._shared_client = None
    yield
    gt._shared_client = None


@pytest.fixture
def gmail_token():
    return StoredToken(
        access_token="ya29.test-access-token",
        refresh_token="1//test-refresh-token",
        token_type="Bearer",
        expires_at=9999999999,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


@pytest.fixture
def sample_gmail_messages():
    """Raw Gmail API response format for message list."""
    return {
        "messages": [
            {"id": "msg-001", "threadId": "thread-001"},
            {"id": "msg-002", "threadId": "thread-002"},
            {"id": "msg-003", "threadId": "thread-003"},
        ],
        "resultSizeEstimate": 3,
    }


@pytest.fixture
def sample_gmail_message_detail():
    """Raw Gmail API response format for a single message."""
    return {
        "id": "msg-001",
        "threadId": "thread-001",
        "labelIds": ["INBOX", "UNREAD"],
        "snippet": "Meeting tomorrow at 3pm",
        "payload": {
            "headers": [
                {"name": "From", "value": "alice@example.com"},
                {"name": "To", "value": "bob@example.com"},
                {"name": "Subject", "value": "Team Meeting"},
                {"name": "Date", "value": "Wed, 11 Mar 2026 10:00:00 +0900"},
            ],
            "mimeType": "text/plain",
            "body": {
                "size": 45,
                "data": "SGVsbG8sIHRoZSBtZWV0aW5nIGlzIHRvbW9ycm93IGF0IDNwbS4=",
            },
        },
        "sizeEstimate": 1200,
        "internalDate": "1741658400000",
    }
