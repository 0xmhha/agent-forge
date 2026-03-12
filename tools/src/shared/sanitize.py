"""Unified token sanitization — single source of truth for all token patterns.

Removes authentication tokens from any text before it reaches LLM responses.
Covers Gmail OAuth, GitHub PAT/OAuth/App/Actions tokens, and generic Bearer tokens.
"""

import re

_TOKEN_PATTERN = re.compile(
    r"|".join([
        r"ya29\.[A-Za-z0-9_-]+",          # Google OAuth access token
        r"ghp_[A-Za-z0-9]+",              # GitHub personal access token (classic)
        r"gho_[A-Za-z0-9]+",              # GitHub OAuth token
        r"github_pat_[A-Za-z0-9_]+",      # GitHub fine-grained PAT
        r"ghs_[A-Za-z0-9]+",              # GitHub server-to-server (App)
        r"ghr_[A-Za-z0-9]+",              # GitHub refresh token
        r"gha_[A-Za-z0-9]+",              # GitHub Actions token
        r"Bearer\s+\S+",                  # Generic Bearer header value
        r"token\s+\S+",                   # Generic token header value
    ]),
    re.IGNORECASE,
)


def sanitize(text: str) -> str:
    """Remove all known token patterns from text.

    Use before including any external API response or error message
    in MCP tool results. This is the last defense against token leakage.
    """
    return _TOKEN_PATTERN.sub("[REDACTED]", text)
