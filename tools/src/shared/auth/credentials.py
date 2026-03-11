"""Credential management — loads auth configs from environment variables."""

import os

from shared.types import AuthConfig, ToolSource


def load_gmail_config() -> AuthConfig:
    """Load Gmail OAuth config from environment variables."""
    return AuthConfig(
        service=ToolSource.GMAIL,
        client_id=os.environ.get("GMAIL_CLIENT_ID", ""),
        client_secret=os.environ.get("GMAIL_CLIENT_SECRET", ""),
        scopes=["https://www.googleapis.com/auth/gmail.readonly"],
    )


def load_github_config() -> AuthConfig:
    """Load GitHub config from environment variables.

    Supports both OAuth app and personal access token.
    PAT is simpler and sufficient for read-only monitoring.
    """
    api_key = os.environ.get("GITHUB_TOKEN", "")
    return AuthConfig(
        service=ToolSource.GITHUB,
        client_id=os.environ.get("GITHUB_CLIENT_ID", ""),
        client_secret=os.environ.get("GITHUB_CLIENT_SECRET", ""),
        api_key=api_key,
        scopes=["repo", "read:org"],
    )


def load_config(service: ToolSource) -> AuthConfig:
    """Load auth config for the specified service."""
    loaders = {
        ToolSource.GMAIL: load_gmail_config,
        ToolSource.GITHUB: load_github_config,
    }
    loader = loaders.get(service)
    if not loader:
        raise ValueError(f"Unknown service: {service}")
    return loader()
