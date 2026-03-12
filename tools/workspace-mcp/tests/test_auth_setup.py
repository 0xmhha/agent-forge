"""Tests for the auth setup web UI."""

import time

import pytest
from fastapi.testclient import TestClient

from shared.auth import setup
from shared.auth.token_store import StoredToken, TokenStore
from shared.types import ToolSource


@pytest.fixture
def token_store(tmp_path):
    return TokenStore(store_dir=tmp_path / "tokens")


@pytest.fixture
def app(token_store, monkeypatch):
    monkeypatch.setattr(setup, "_build_token_store", lambda: token_store)
    return setup.create_app()


@pytest.fixture
def client(app):
    return TestClient(app)


class TestIndexPage:
    def test_renders_html(self, client):
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 200
        assert "agent-forge" in response.text
        assert "Gmail" in response.text
        assert "GitHub" in response.text

    def test_shows_disconnected_status(self, client):
        response = client.get("/")
        assert "미연결" in response.text or "자격증명 없음" in response.text

    def test_shows_connected_status(self, client, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(
                access_token="test-token",
                refresh_token="test-refresh",
                expires_at=int(time.time()) + 3600,
                scopes=["https://www.googleapis.com/auth/gmail.readonly"],
            ),
        )
        response = client.get("/")
        assert "연결됨" in response.text

    def test_shows_expired_status(self, client, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(
                access_token="test-token",
                expires_at=int(time.time()) - 100,
            ),
        )
        response = client.get("/")
        assert "만료됨" in response.text

    def test_displays_message(self, client):
        response = client.get("/?message=테스트 메시지")
        assert "테스트 메시지" in response.text


class TestConnect:
    def test_connect_unknown_service_redirects(self, client):
        response = client.get("/connect/unknown", follow_redirects=False)
        assert response.status_code == 307
        assert "message=" in response.headers["location"]

    def test_connect_without_credentials_redirects(self, client, monkeypatch):
        monkeypatch.delenv("GMAIL_CLIENT_ID", raising=False)
        monkeypatch.delenv("GMAIL_CLIENT_SECRET", raising=False)
        response = client.get("/connect/gmail", follow_redirects=False)
        assert response.status_code == 307
        assert "환경변수" in response.headers["location"] or "message=" in response.headers["location"]

    def test_connect_with_credentials_redirects_to_oauth(self, client, monkeypatch):
        monkeypatch.setenv("GMAIL_CLIENT_ID", "test-client-id")
        monkeypatch.setenv("GMAIL_CLIENT_SECRET", "test-client-secret")
        response = client.get("/connect/gmail", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "accounts.google.com" in location
        assert "test-client-id" in location

    def test_connect_github_redirects_to_oauth(self, client, monkeypatch):
        monkeypatch.setenv("GITHUB_CLIENT_ID", "gh-test-id")
        monkeypatch.setenv("GITHUB_CLIENT_SECRET", "gh-test-secret")
        response = client.get("/connect/github", follow_redirects=False)
        assert response.status_code == 307
        location = response.headers["location"]
        assert "github.com/login/oauth/authorize" in location


class TestCallback:
    def test_callback_with_error(self, client):
        response = client.get(
            "/callback/gmail?error=access_denied&error_description=User+denied",
            follow_redirects=False,
        )
        assert response.status_code == 307
        assert "인증 실패" in response.headers["location"] or "message=" in response.headers["location"]

    def test_callback_without_code(self, client):
        response = client.get("/callback/gmail", follow_redirects=False)
        assert response.status_code == 307
        assert "message=" in response.headers["location"]


class TestDisconnect:
    def test_disconnect_removes_token(self, client, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(access_token="test-token"),
        )
        assert token_store.exists(ToolSource.GMAIL)

        response = client.get("/disconnect/gmail", follow_redirects=False)
        assert response.status_code == 307
        assert not token_store.exists(ToolSource.GMAIL)

    def test_disconnect_nonexistent_is_safe(self, client, token_store):
        assert not token_store.exists(ToolSource.GMAIL)
        response = client.get("/disconnect/gmail", follow_redirects=False)
        assert response.status_code == 307


class TestServiceStatus:
    def test_no_token_returns_disconnected(self, token_store):
        status = setup._get_service_status(token_store, ToolSource.GMAIL)
        assert not status["connected"]

    def test_valid_token_returns_connected(self, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(
                access_token="test",
                expires_at=int(time.time()) + 3600,
            ),
        )
        status = setup._get_service_status(token_store, ToolSource.GMAIL)
        assert status["connected"]
        assert not status["expired"]

    def test_expired_token_detected(self, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(
                access_token="test",
                expires_at=int(time.time()) - 100,
            ),
        )
        status = setup._get_service_status(token_store, ToolSource.GMAIL)
        assert status["connected"]
        assert status["expired"]

    def test_no_expiry_means_not_expired(self, token_store):
        token_store.save(
            ToolSource.GMAIL,
            StoredToken(access_token="test", expires_at=0),
        )
        status = setup._get_service_status(token_store, ToolSource.GMAIL)
        assert status["connected"]
        assert not status["expired"]
