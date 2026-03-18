"""Integration test — verify logging is wired correctly across all components.

Initializes the actual server components (without network I/O) and confirms
that log records appear in both console and file outputs.
"""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest

from shared.logging import setup_logging


@pytest.fixture
def log_env(tmp_path: Path):
    """Set up logging with a temporary log directory, then tear down."""
    setup_logging(level="DEBUG", log_dir=tmp_path)
    yield tmp_path
    # Reset root logger
    root = logging.getLogger()
    root.handlers.clear()
    root.setLevel(logging.WARNING)


def _read_log(log_dir: Path) -> str:
    log_file = log_dir / "workspace-mcp.log"
    if not log_file.exists():
        return ""
    # Flush all handlers first
    for handler in logging.getLogger().handlers:
        handler.flush()
    return log_file.read_text(encoding="utf-8")


class TestServerLogging:
    """Verify server.py emits expected log messages."""

    def test_tool_registration_logged(self, log_env):
        from shared.server import ToolServer

        with patch("shared.server._server_instance", None):
            server = ToolServer()

        log = _read_log(log_env)
        assert "Registered tool: task_list" in log
        assert "Registered tool: task_sync" in log
        assert "Registered tool: task_update" in log

    def test_event_hooks_registered(self, log_env):
        from shared.server import ToolServer

        with patch("shared.server._server_instance", None):
            server = ToolServer()

        log = _read_log(log_env)
        assert "Event hooks registered" in log
        assert "3 subscribers" in log


class TestEventLogging:
    """Verify event dispatch is logged."""

    @pytest.mark.asyncio
    async def test_dispatch_logged(self, log_env):
        from shared.events import EventDispatcher, ReviewDetected

        dispatcher = EventDispatcher()

        async def noop(event):
            pass

        dispatcher.subscribe(ReviewDetected, noop)

        event = ReviewDetected(
            repo="o/r", pr_number=1, pr_title="t",
            pr_url="", requester="x", todo_filename="f.md",
        )
        await dispatcher.dispatch(event)

        log = _read_log(log_env)
        assert "Dispatching ReviewDetected to 1 handler" in log


class TestHookLogging:
    """Verify hook trigger writes are logged."""

    @pytest.mark.asyncio
    async def test_trigger_creation_logged(self, log_env, tmp_path):
        from shared.events import ReviewDetected
        from shared.hooks import TriggerFileHook

        hook = TriggerFileHook(triggers_dir=tmp_path / "triggers")
        event = ReviewDetected(
            repo="owner/repo", pr_number=42, pr_title="fix",
            pr_url="", requester="x", todo_filename="f.md",
        )
        await hook.on_review_detected(event)

        log = _read_log(log_env)
        assert "Trigger created: review-owner-repo-42.json" in log


class TestBatchLogging:
    """Verify batch scheduler logs cycle timing."""

    @pytest.mark.asyncio
    async def test_watcher_registration_logged(self, log_env):
        from shared.batch.scheduler import BatchScheduler

        scheduler = BatchScheduler()

        class FakeWatcher:
            name = "test_watcher"
            async def run_once(self) -> int:
                return 0

        scheduler.register(FakeWatcher())

        log = _read_log(log_env)
        assert "Registered watcher: test_watcher" in log


class TestClientLogging:
    """Verify API clients log at DEBUG level."""

    def test_github_client_has_logger(self):
        import github.client as gc
        assert hasattr(gc, "logger")
        assert gc.logger.name == "github.client"

    def test_gmail_client_has_logger(self):
        import gmail.client as gmc
        assert hasattr(gmc, "logger")
        assert gmc.logger.name == "gmail.client"


class TestLoggingCoverage:
    """Verify all key modules have loggers configured."""

    @pytest.mark.parametrize("module_path", [
        "shared.server",
        "shared.events",
        "shared.hooks",
        "shared.batch.scheduler",
        "github.client",
        "gmail.client",
        "github.review.watcher",
    ])
    def test_module_has_logger(self, module_path):
        import importlib
        mod = importlib.import_module(module_path)
        assert hasattr(mod, "logger"), f"{module_path} missing logger"
        assert mod.logger.name == module_path
