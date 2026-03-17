"""Centralized logging configuration for workspace-mcp.

Provides file rotation, structured console output, and configurable log levels.
MCP servers use stdio for protocol transport, so all logs go to stderr + file.

Usage:
    from shared.logging import setup_logging
    setup_logging()  # reads LOG_LEVEL env var, defaults to INFO
"""

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
_LOG_FILE = "workspace-mcp.log"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3
_DEFAULT_LEVEL = "INFO"

_CONSOLE_FMT = "%(asctime)s [%(levelname)-7s] %(name)s — %(message)s"
_CONSOLE_DATE_FMT = "%H:%M:%S"
_FILE_FMT = "%(asctime)s [%(levelname)-7s] %(name)s:%(lineno)d — %(message)s"
_FILE_DATE_FMT = "%Y-%m-%d %H:%M:%S"

# ANSI color codes for terminal output
_LEVEL_COLORS = {
    "DEBUG": "\033[36m",     # cyan
    "INFO": "\033[32m",      # green
    "WARNING": "\033[33m",   # yellow
    "ERROR": "\033[31m",     # red
    "CRITICAL": "\033[1;31m",  # bold red
}
_RESET = "\033[0m"


class ColorFormatter(logging.Formatter):
    """Console formatter with ANSI colors when stderr is a TTY."""

    def __init__(self, use_color: bool = True) -> None:
        super().__init__(fmt=_CONSOLE_FMT, datefmt=_CONSOLE_DATE_FMT)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        msg = super().format(record)
        if self._use_color:
            color = _LEVEL_COLORS.get(record.levelname, "")
            if color:
                return f"{color}{msg}{_RESET}"
        return msg


def setup_logging(
    level: str | None = None,
    log_dir: Path | None = None,
    enable_file: bool = True,
    enable_console: bool = True,
) -> None:
    """Configure root logger with file rotation and colored console output.

    Level resolution: level param > LOG_LEVEL env var > INFO default.
    Console output goes to stderr (not stdout, to avoid MCP protocol conflicts).
    """
    resolved_level = _resolve_level(level)
    root = logging.getLogger()
    root.setLevel(resolved_level)

    # Clear existing handlers to avoid duplicates on re-init
    root.handlers.clear()

    if enable_console:
        root.addHandler(_create_console_handler(resolved_level))

    if enable_file:
        target_dir = log_dir or _LOG_DIR
        root.addHandler(_create_file_handler(target_dir, resolved_level))

    # Suppress noisy third-party loggers
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("mcp").setLevel(logging.WARNING)


def get_log_dir() -> Path:
    """Return the log directory path."""
    return _LOG_DIR


def _resolve_level(level: str | None) -> int:
    """Resolve log level from param, env var, or default."""
    name = (level or os.environ.get("LOG_LEVEL", _DEFAULT_LEVEL)).upper()
    numeric = getattr(logging, name, None)
    if not isinstance(numeric, int):
        numeric = logging.INFO
    return numeric


def _create_console_handler(level: int) -> logging.StreamHandler:
    """Create stderr handler with optional color formatting."""
    handler = logging.StreamHandler(stream=sys.stderr)
    handler.setLevel(level)
    use_color = hasattr(sys.stderr, "isatty") and sys.stderr.isatty()
    handler.setFormatter(ColorFormatter(use_color=use_color))
    return handler


def _create_file_handler(log_dir: Path, level: int) -> RotatingFileHandler:
    """Create rotating file handler. Creates log directory if needed."""
    log_dir.mkdir(parents=True, exist_ok=True)
    handler = RotatingFileHandler(
        log_dir / _LOG_FILE,
        maxBytes=_MAX_BYTES,
        backupCount=_BACKUP_COUNT,
        encoding="utf-8",
    )
    handler.setLevel(level)
    handler.setFormatter(logging.Formatter(fmt=_FILE_FMT, datefmt=_FILE_DATE_FMT))
    return handler
