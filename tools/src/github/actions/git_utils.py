"""Git subprocess utilities for environment setup actions.

Wraps git commands in a safe interface. Uses asyncio.create_subprocess_exec
(not shell=True) to prevent command injection. Clone URLs use HTTPS
without embedded tokens.
"""

import asyncio
import logging
import re

logger = logging.getLogger(__name__)

_TOKEN_PATTERN = re.compile(r"ghp_[A-Za-z0-9]+|gho_[A-Za-z0-9]+|Bearer\s+\S+", re.IGNORECASE)


async def run_git(*args: str, cwd: str | None = None) -> tuple[bool, str]:
    """Run a git command and return (success, output).

    Uses create_subprocess_exec (argument list, no shell) to prevent
    command injection. Output is sanitized to remove any token leaks.
    """
    cmd = ["git", *args]
    logger.info("Running: %s", " ".join(cmd))

    proc = await asyncio.create_subprocess_exec(
        *cmd,
        cwd=cwd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
    )
    stdout, _ = await proc.communicate()
    output = stdout.decode("utf-8", errors="replace").strip()
    sanitized = _TOKEN_PATTERN.sub("[REDACTED]", output)

    return proc.returncode == 0, sanitized


def clone_url(repo: str) -> str:
    """Build HTTPS clone URL without tokens."""
    return f"https://github.com/{repo}.git"
