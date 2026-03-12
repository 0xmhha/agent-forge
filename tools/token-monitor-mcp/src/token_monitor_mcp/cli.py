"""Thin wrapper around the token-monitor Go binary."""

from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path

_BIN_DIR = Path(__file__).resolve().parent.parent.parent / "bin"
_BINARY = _BIN_DIR / "token-monitor"


@dataclass(frozen=True)
class TokenSummary:
    """Parsed token usage summary from token-monitor."""

    session_id: str
    total: int
    input: int
    output: int
    cache_read: int
    cache_create: int
    cost_usd: float
    duration_minutes: int
    date: str
    project: str


def _run(args: list[str], *, timeout: int = 30) -> str:
    """Execute token-monitor binary and return stdout."""
    if not _BINARY.exists():
        raise FileNotFoundError(
            f"token-monitor binary not found at {_BINARY}. "
            f"Place the binary in bin/ directory."
        )

    result = subprocess.run(
        [str(_BINARY), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
    )

    if result.returncode != 0:
        raise RuntimeError(
            f"token-monitor exited with code {result.returncode}: {result.stderr.strip()}"
        )

    return result.stdout


def get_version() -> str:
    """Get token-monitor binary version."""
    output = _run(["help"])
    for line in output.splitlines():
        if line.startswith("token-monitor v"):
            return line.split()[1]
    return "unknown"


def list_sessions() -> list[dict]:
    """List available sessions."""
    output = _run(["session", "list", "--json"])
    try:
        return json.loads(output)
    except json.JSONDecodeError:
        return []


def get_session_summary(identifier: str) -> TokenSummary:
    """Export session in agent-forge format and parse into TokenSummary."""
    output = _run(["session", "export", identifier, "--format", "agent-forge"])
    data = json.loads(output)
    tokens = data.get("tokens", {})

    return TokenSummary(
        session_id=data.get("session_id", ""),
        total=tokens.get("total", 0),
        input=tokens.get("input", 0),
        output=tokens.get("output", 0),
        cache_read=tokens.get("cache_read", 0),
        cache_create=tokens.get("cache_create", 0),
        cost_usd=tokens.get("cost_usd", 0.0) or 0.0,
        duration_minutes=data.get("duration_minutes", 0),
        date=data.get("date", ""),
        project=data.get("project", ""),
    )


def export_session(identifier: str, fmt: str = "agent-forge") -> str:
    """Export session data in the specified format."""
    return _run(["session", "export", identifier, "--format", fmt])
