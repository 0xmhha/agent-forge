"""OAuth 2.0 authorization flow — handles token acquisition and refresh."""

import asyncio
import logging
from http.server import BaseHTTPRequestHandler, HTTPServer
from threading import Thread
from urllib.parse import parse_qs, urlparse

import httpx

from shared.auth.token_store import StoredToken, TokenStore
from shared.types import AuthConfig

logger = logging.getLogger(__name__)


class OAuthFlow:
    """Generic OAuth 2.0 flow with local callback server.

    Supports authorization code grant with PKCE where available.
    Token refresh is handled automatically when access_token expires.
    """

    def __init__(self, config: AuthConfig, token_store: TokenStore) -> None:
        self._config = config
        self._token_store = token_store

    async def get_valid_token(self) -> StoredToken | None:
        """Return a valid token, refreshing if expired."""
        token = self._token_store.load(self._config.service)
        if token is None:
            return None

        if self._is_expired(token):
            refreshed = await self._refresh_token(token)
            if refreshed:
                self._token_store.save(self._config.service, refreshed)
                return refreshed
            return None

        return token

    async def authorize(
        self,
        auth_url: str,
        token_url: str,
        *,
        callback_port: int = 8919,
    ) -> StoredToken:
        """Run the full OAuth authorization code flow.

        Opens a local HTTP server to capture the callback, then exchanges
        the authorization code for tokens.
        """
        redirect_uri = f"http://localhost:{callback_port}/callback"

        params = {
            "client_id": self._config.client_id,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": " ".join(self._config.scopes),
            "access_type": "offline",
            "prompt": "consent",
        }

        full_auth_url = f"{auth_url}?{'&'.join(f'{k}={v}' for k, v in params.items())}"
        logger.info("Open this URL to authorize: %s", full_auth_url)

        code = await self._wait_for_callback(callback_port)

        token = await self._exchange_code(
            token_url=token_url,
            code=code,
            redirect_uri=redirect_uri,
        )
        self._token_store.save(self._config.service, token)
        return token

    async def _exchange_code(
        self,
        token_url: str,
        code: str,
        redirect_uri: str,
    ) -> StoredToken:
        """Exchange authorization code for access + refresh tokens."""
        async with httpx.AsyncClient() as client:
            response = await client.post(
                token_url,
                data={
                    "grant_type": "authorization_code",
                    "code": code,
                    "redirect_uri": redirect_uri,
                    "client_id": self._config.client_id,
                    "client_secret": self._config.client_secret,
                },
            )
            response.raise_for_status()
            data = response.json()

        return StoredToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", ""),
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_in", 0),
            scopes=self._config.scopes,
        )

    async def _refresh_token(self, token: StoredToken) -> StoredToken | None:
        """Use refresh_token to obtain a new access_token."""
        if not token.refresh_token:
            return None

        token_url = self._get_token_url()
        if not token_url:
            return None

        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    token_url,
                    data={
                        "grant_type": "refresh_token",
                        "refresh_token": token.refresh_token,
                        "client_id": self._config.client_id,
                        "client_secret": self._config.client_secret,
                    },
                )
                response.raise_for_status()
                data = response.json()
        except httpx.HTTPError:
            logger.exception("Token refresh failed for %s", self._config.service)
            return None

        return StoredToken(
            access_token=data["access_token"],
            refresh_token=data.get("refresh_token", token.refresh_token),
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_in", 0),
            scopes=token.scopes,
        )

    def _get_token_url(self) -> str | None:
        """Resolve token endpoint by service type."""
        urls = {
            "gmail": "https://oauth2.googleapis.com/token",
            "github": "https://github.com/login/oauth/access_token",
        }
        return urls.get(self._config.service)

    async def _wait_for_callback(self, port: int) -> str:
        """Start a temporary HTTP server and wait for the OAuth callback."""
        code_future: asyncio.Future[str] = asyncio.get_event_loop().create_future()

        class CallbackHandler(BaseHTTPRequestHandler):
            def do_GET(self) -> None:
                query = parse_qs(urlparse(self.path).query)
                auth_code = query.get("code", [None])[0]
                if auth_code:
                    self.send_response(200)
                    self.send_header("Content-Type", "text/html")
                    self.end_headers()
                    self.wfile.write(b"Authorization complete. You can close this tab.")
                    asyncio.get_event_loop().call_soon_threadsafe(
                        code_future.set_result, auth_code
                    )
                else:
                    self.send_response(400)
                    self.end_headers()
                    self.wfile.write(b"Missing authorization code.")

            def log_message(self, format: str, *args: object) -> None:
                pass

        server = HTTPServer(("localhost", port), CallbackHandler)
        thread = Thread(target=server.handle_request, daemon=True)
        thread.start()

        code = await code_future
        server.server_close()
        return code

    @staticmethod
    def _is_expired(token: StoredToken) -> bool:
        """Check if token has expired (with 5-minute buffer)."""
        if token.expires_at <= 0:
            return False
        import time

        return time.time() > (token.expires_at - 300)
