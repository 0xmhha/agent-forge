"""Tests for token-monitor MCP server handlers."""

from __future__ import annotations

import json
from unittest.mock import patch

import pytest

from token_monitor_mcp.cli import TokenSummary
from token_monitor_mcp.server import (
    _handle_session_list,
    _handle_session_summary,
    _handle_session_export,
    _handle_cost_check,
    _handle_version,
)


SAMPLE_SUMMARY = TokenSummary(
    session_id="test-session",
    total=10000,
    input=6000,
    output=4000,
    cache_read=1000,
    cache_create=500,
    cost_usd=0.12,
    duration_minutes=45,
    date="2026-03-12",
    project="agent-forge",
)


class TestHandleSessionList:
    def test_returns_sessions_with_count(self):
        sessions = [{"id": "a"}, {"id": "b"}]
        with patch("token_monitor_mcp.server.list_sessions", return_value=sessions):
            result = _handle_session_list()
            assert result["success"] is True
            assert result["data"]["count"] == 2
            assert result["data"]["sessions"] == sessions

    def test_empty_sessions(self):
        with patch("token_monitor_mcp.server.list_sessions", return_value=[]):
            result = _handle_session_list()
            assert result["success"] is True
            assert result["data"]["count"] == 0


class TestHandleSessionSummary:
    def test_returns_token_breakdown(self):
        with patch("token_monitor_mcp.server.get_session_summary", return_value=SAMPLE_SUMMARY):
            result = _handle_session_summary("test-session")
            assert result["success"] is True
            tokens = result["data"]["tokens"]
            assert tokens["total"] == 10000
            assert tokens["input"] == 6000
            assert tokens["output"] == 4000
            assert tokens["cache_read"] == 1000
            assert tokens["cache_create"] == 500
            assert result["data"]["cost_usd"] == 0.12
            assert result["data"]["duration_minutes"] == 45


class TestHandleSessionExport:
    def test_agent_forge_format_parses_json(self):
        export_data = {"session_id": "test", "tokens": {"total": 100}}
        with patch(
            "token_monitor_mcp.server.export_session",
            return_value=json.dumps(export_data),
        ):
            result = _handle_session_export("test", "agent-forge")
            assert result["success"] is True
            assert result["data"]["session_id"] == "test"

    def test_csv_format_returns_raw(self):
        csv_data = "timestamp,tokens\n2026-03-12,100"
        with patch("token_monitor_mcp.server.export_session", return_value=csv_data):
            result = _handle_session_export("test", "csv")
            assert result["success"] is True
            assert result["data"]["raw"] == csv_data


class TestHandleCostCheck:
    def test_returns_cost_and_tokens(self):
        with patch("token_monitor_mcp.server.get_session_summary", return_value=SAMPLE_SUMMARY):
            result = _handle_cost_check("test-session")
            assert result["success"] is True
            assert result["data"]["cost_usd"] == 0.12
            assert result["data"]["total_tokens"] == 10000
            assert result["data"]["duration_minutes"] == 45


class TestHandleVersion:
    def test_returns_version(self):
        with patch("token_monitor_mcp.server.get_version", return_value="v0.2.0"):
            result = _handle_version()
            assert result["success"] is True
            assert result["data"]["version"] == "v0.2.0"
