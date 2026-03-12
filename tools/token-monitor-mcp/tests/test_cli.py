"""Tests for token-monitor CLI wrapper."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from token_monitor_mcp.cli import (
    TokenSummary,
    _run,
    get_version,
    list_sessions,
    get_session_summary,
    export_session,
)


class TestRun:
    """Tests for the _run helper function."""

    def test_binary_not_found(self, tmp_path):
        with patch("token_monitor_mcp.cli._BINARY", tmp_path / "nonexistent"):
            with pytest.raises(FileNotFoundError, match="token-monitor binary not found"):
                _run(["help"])

    def test_nonzero_exit_code(self):
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "some error"

        with patch("token_monitor_mcp.cli.subprocess.run", return_value=mock_result):
            with patch("token_monitor_mcp.cli._BINARY") as mock_bin:
                mock_bin.exists.return_value = True
                with pytest.raises(RuntimeError, match="exited with code 1"):
                    _run(["bad-command"])

    def test_success(self):
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"

        with patch("token_monitor_mcp.cli.subprocess.run", return_value=mock_result):
            with patch("token_monitor_mcp.cli._BINARY") as mock_bin:
                mock_bin.exists.return_value = True
                assert _run(["help"]) == "output"


class TestGetVersion:
    """Tests for get_version."""

    def test_parses_version(self):
        with patch("token_monitor_mcp.cli._run", return_value="token-monitor v0.2.0\nUsage:"):
            assert get_version() == "v0.2.0"

    def test_unknown_version(self):
        with patch("token_monitor_mcp.cli._run", return_value="unexpected output"):
            assert get_version() == "unknown"


class TestListSessions:
    """Tests for list_sessions."""

    def test_parses_json_output(self):
        sessions = [{"id": "abc", "name": "test"}]
        with patch("token_monitor_mcp.cli._run", return_value=json.dumps(sessions)):
            assert list_sessions() == sessions

    def test_invalid_json_returns_empty(self):
        with patch("token_monitor_mcp.cli._run", return_value="not json"):
            assert list_sessions() == []


class TestGetSessionSummary:
    """Tests for get_session_summary."""

    def test_parses_agent_forge_output(self):
        data = {
            "session_id": "abc-123",
            "date": "2026-03-12",
            "project": "test-proj",
            "tokens": {
                "total": 5000,
                "input": 3000,
                "output": 2000,
                "cache_read": 500,
                "cache_create": 200,
                "cost_usd": 0.05,
            },
            "duration_minutes": 30,
        }
        with patch("token_monitor_mcp.cli._run", return_value=json.dumps(data)):
            summary = get_session_summary("abc-123")

            assert summary.session_id == "abc-123"
            assert summary.total == 5000
            assert summary.input == 3000
            assert summary.output == 2000
            assert summary.cache_read == 500
            assert summary.cache_create == 200
            assert summary.cost_usd == 0.05
            assert summary.duration_minutes == 30

    def test_missing_fields_default_to_zero(self):
        data = {
            "session_id": "minimal",
            "tokens": {},
            "duration_minutes": 0,
        }
        with patch("token_monitor_mcp.cli._run", return_value=json.dumps(data)):
            summary = get_session_summary("minimal")
            assert summary.total == 0
            assert summary.cost_usd == 0.0


class TestExportSession:
    """Tests for export_session."""

    def test_passes_format_flag(self):
        with patch("token_monitor_mcp.cli._run", return_value="{}") as mock_run:
            export_session("test", "csv")
            mock_run.assert_called_once_with(
                ["session", "export", "test", "--format", "csv"]
            )

    def test_defaults_to_agent_forge(self):
        with patch("token_monitor_mcp.cli._run", return_value="{}") as mock_run:
            export_session("test")
            mock_run.assert_called_once_with(
                ["session", "export", "test", "--format", "agent-forge"]
            )
