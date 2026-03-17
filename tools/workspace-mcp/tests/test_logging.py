"""Tests for the centralized logging module."""

import logging
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.logging import ColorFormatter, setup_logging


@pytest.fixture(autouse=True)
def _clean_root_logger():
    """Reset root logger between tests."""
    root = logging.getLogger()
    original_handlers = root.handlers[:]
    original_level = root.level
    yield
    root.handlers = original_handlers
    root.level = original_level


def test_setup_logging_creates_handlers(tmp_path: Path):
    setup_logging(log_dir=tmp_path)
    root = logging.getLogger()

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_file_only(tmp_path: Path):
    setup_logging(log_dir=tmp_path, enable_console=False)
    root = logging.getLogger()

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" not in handler_types
    assert "RotatingFileHandler" in handler_types


def test_setup_logging_console_only():
    setup_logging(enable_file=False)
    root = logging.getLogger()

    handler_types = [type(h).__name__ for h in root.handlers]
    assert "StreamHandler" in handler_types
    assert "RotatingFileHandler" not in handler_types


def test_log_level_default(tmp_path: Path):
    setup_logging(log_dir=tmp_path)
    root = logging.getLogger()
    assert root.level == logging.INFO


def test_log_level_from_param(tmp_path: Path):
    setup_logging(level="DEBUG", log_dir=tmp_path)
    root = logging.getLogger()
    assert root.level == logging.DEBUG


def test_log_level_from_env(tmp_path: Path):
    with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
        setup_logging(log_dir=tmp_path)
    root = logging.getLogger()
    assert root.level == logging.WARNING


def test_log_level_param_overrides_env(tmp_path: Path):
    with patch.dict(os.environ, {"LOG_LEVEL": "WARNING"}):
        setup_logging(level="ERROR", log_dir=tmp_path)
    root = logging.getLogger()
    assert root.level == logging.ERROR


def test_invalid_log_level_falls_back_to_info(tmp_path: Path):
    setup_logging(level="INVALID_LEVEL", log_dir=tmp_path)
    root = logging.getLogger()
    assert root.level == logging.INFO


def test_file_handler_creates_log_dir(tmp_path: Path):
    log_dir = tmp_path / "nested" / "logs"
    setup_logging(log_dir=log_dir)
    assert log_dir.exists()
    assert (log_dir / "workspace-mcp.log").exists()


def test_file_handler_writes_log(tmp_path: Path):
    setup_logging(log_dir=tmp_path)
    test_logger = logging.getLogger("test.file_write")
    test_logger.info("test message for file")

    # Flush handlers
    for handler in logging.getLogger().handlers:
        handler.flush()

    log_content = (tmp_path / "workspace-mcp.log").read_text()
    assert "test message for file" in log_content


def test_color_formatter_with_color():
    formatter = ColorFormatter(use_color=True)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    output = formatter.format(record)
    assert "\033[32m" in output  # green for INFO
    assert "\033[0m" in output   # reset


def test_color_formatter_without_color():
    formatter = ColorFormatter(use_color=False)
    record = logging.LogRecord(
        name="test", level=logging.INFO, pathname="", lineno=0,
        msg="hello", args=(), exc_info=None,
    )
    output = formatter.format(record)
    assert "\033[" not in output


def test_noisy_loggers_suppressed(tmp_path: Path):
    setup_logging(level="DEBUG", log_dir=tmp_path)
    assert logging.getLogger("httpx").level == logging.WARNING
    assert logging.getLogger("httpcore").level == logging.WARNING
    assert logging.getLogger("mcp").level == logging.WARNING


def test_setup_clears_duplicate_handlers(tmp_path: Path):
    setup_logging(log_dir=tmp_path)
    setup_logging(log_dir=tmp_path)
    root = logging.getLogger()
    # Should not have duplicate handlers after calling twice
    handler_types = [type(h).__name__ for h in root.handlers]
    assert handler_types.count("StreamHandler") == 1
    assert handler_types.count("RotatingFileHandler") == 1
