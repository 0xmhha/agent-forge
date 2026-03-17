"""Tests for TokenStore — encrypted token storage."""

import pytest

from shared.auth.token_store import StoredToken, TokenStore


@pytest.fixture
def sample_token():
    return StoredToken(
        access_token="ya29.test-access-token-value",
        refresh_token="1//test-refresh-token-value",
        token_type="Bearer",
        expires_at=9999999999,
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


class TestTokenStoreRoundTrip:
    """Tokens should survive save → load cycle with encryption."""

    def test_save_and_load_returns_same_token(self, token_store, sample_token):
        token_store.save("gmail", sample_token)
        loaded = token_store.load("gmail")

        assert loaded is not None
        assert loaded.access_token == sample_token.access_token
        assert loaded.refresh_token == sample_token.refresh_token
        assert loaded.token_type == sample_token.token_type
        assert loaded.expires_at == sample_token.expires_at
        assert loaded.scopes == sample_token.scopes

    def test_load_nonexistent_returns_none(self, token_store):
        loaded = token_store.load("nonexistent_service")

        assert loaded is None

    def test_overwrite_updates_token(self, token_store, sample_token):
        token_store.save("gmail", sample_token)

        updated = StoredToken(
            access_token="ya29.new-token",
            refresh_token="1//new-refresh",
            token_type="Bearer",
            expires_at=8888888888,
            scopes=["https://www.googleapis.com/auth/gmail.readonly"],
        )
        token_store.save("gmail", updated)
        loaded = token_store.load("gmail")

        assert loaded is not None
        assert loaded.access_token == "ya29.new-token"

    def test_different_services_stored_separately(self, token_store, sample_token):
        github_token = StoredToken(
            access_token="ghp_test-github-token",
            refresh_token="",
            token_type="Bearer",
            expires_at=0,
            scopes=[],
        )
        token_store.save("gmail", sample_token)
        token_store.save("github", github_token)

        gmail_loaded = token_store.load("gmail")
        github_loaded = token_store.load("github")

        assert gmail_loaded.access_token == sample_token.access_token
        assert github_loaded.access_token == "ghp_test-github-token"


class TestTokenStoreEncryption:
    """Stored files should be encrypted, not plaintext."""

    def test_file_content_is_not_plaintext(self, token_store, sample_token, tmp_dir):
        token_store.save("gmail", sample_token)

        token_file = tmp_dir / "tokens" / "gmail.token"
        raw_content = token_file.read_bytes()

        assert b"ya29.test-access-token-value" not in raw_content
        assert b"1//test-refresh-token-value" not in raw_content

    def test_creates_store_directory(self, tmp_dir):
        store_path = tmp_dir / "new_tokens"
        store = TokenStore(store_dir=store_path)
        token = StoredToken(
            access_token="test", refresh_token="", token_type="Bearer",
            expires_at=0, scopes=[],
        )
        store.save("test", token)

        assert store_path.exists()
