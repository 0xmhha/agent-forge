"""Template for an external API client.

The client handles authentication and API calls.
Tokens are managed by shared.auth — never exposed to MCP responses.
"""

import httpx

from shared.auth.token_store import StoredToken


class ExampleClient:
    """API client for the example service."""

    BASE_URL = "https://api.example.com"

    def __init__(self, token: StoredToken) -> None:
        self._headers = {
            "Authorization": f"{token.token_type} {token.access_token}",
            "Accept": "application/json",
        }

    async def get_items(self, query: str = "") -> list[dict]:
        """Fetch items from the API. Returns data only, no auth details."""
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.BASE_URL}/items",
                headers=self._headers,
                params={"q": query} if query else {},
            )
            response.raise_for_status()
            return response.json().get("items", [])
