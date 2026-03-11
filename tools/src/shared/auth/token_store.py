"""Encrypted token storage — tokens never leave this module except to API clients."""

import json
import os
from pathlib import Path

from cryptography.fernet import Fernet, InvalidToken
from pydantic import BaseModel


class StoredToken(BaseModel):
    """Token data persisted to disk in encrypted form."""

    access_token: str
    refresh_token: str = ""
    token_type: str = "Bearer"
    expires_at: int = 0
    scopes: list[str] = []


class TokenStore:
    """Fernet-encrypted file-based token storage.

    Encryption key is loaded from AGENT_FORGE_KEY environment variable.
    If not set, a new key is generated and must be saved by the caller.
    """

    def __init__(self, store_dir: str | Path | None = None) -> None:
        self._store_dir = Path(store_dir) if store_dir else self._default_store_dir()
        self._store_dir.mkdir(parents=True, exist_ok=True)
        self._fernet = Fernet(self._load_or_create_key())

    def save(self, service: str, token: StoredToken) -> None:
        """Encrypt and persist a token for the given service."""
        payload = token.model_dump_json().encode()
        encrypted = self._fernet.encrypt(payload)
        token_path = self._token_path(service)
        token_path.write_bytes(encrypted)
        token_path.chmod(0o600)

    def load(self, service: str) -> StoredToken | None:
        """Load and decrypt a token. Returns None if not found or corrupted."""
        token_path = self._token_path(service)
        if not token_path.exists():
            return None
        try:
            encrypted = token_path.read_bytes()
            decrypted = self._fernet.decrypt(encrypted)
            return StoredToken.model_validate_json(decrypted)
        except (InvalidToken, json.JSONDecodeError):
            return None

    def delete(self, service: str) -> bool:
        """Remove stored token for the given service."""
        token_path = self._token_path(service)
        if token_path.exists():
            token_path.unlink()
            return True
        return False

    def exists(self, service: str) -> bool:
        """Check if a token exists for the given service."""
        return self._token_path(service).exists()

    def _token_path(self, service: str) -> Path:
        return self._store_dir / f"{service}.token"

    def _load_or_create_key(self) -> bytes:
        env_key = os.environ.get("AGENT_FORGE_KEY")
        if env_key:
            return env_key.encode()

        key_path = self._store_dir / ".key"
        if key_path.exists():
            return key_path.read_bytes().strip()

        key = Fernet.generate_key()
        key_path.write_bytes(key)
        key_path.chmod(0o600)
        return key

    @staticmethod
    def _default_store_dir() -> Path:
        return Path.home() / ".agent-forge" / "tokens"
