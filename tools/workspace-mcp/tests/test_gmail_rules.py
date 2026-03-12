"""Tests for Gmail rule-based email processing."""

import pytest

from gmail.rules.classifier import EmailAction, classify_email
from gmail.rules.jira_detector import (
    JiraDetectionResult,
    detect_jira,
    extract_ticket_keys,
)
from gmail.rules.processor import process_email, process_inbox


# ── Jira Detector ──────────────────────────────────────────────────────


class TestJiraDetector:
    def test_detects_jira_sender(self):
        email = {"sender": "jira@company.atlassian.net", "subject": "Update", "body": ""}
        result = detect_jira(email)
        assert result.is_jira_email
        assert "jira_sender" in result.source_signals

    def test_detects_jira_subject_prefix(self):
        email = {
            "sender": "noreply@company.com",
            "subject": "[JIRA] (PROJ-123) Task title",
            "body": "",
        }
        result = detect_jira(email)
        assert result.is_jira_email
        assert "jira_subject_prefix" in result.source_signals

    def test_detects_ticket_key_in_subject(self):
        email = {
            "sender": "someone@company.com",
            "subject": "Please look at FEAT-456",
            "body": "",
        }
        result = detect_jira(email)
        assert len(result.tickets) == 1
        assert result.tickets[0].key == "FEAT-456"
        assert result.tickets[0].project == "FEAT"

    def test_detects_jira_url_in_body(self):
        email = {
            "sender": "someone@company.com",
            "subject": "Check this issue",
            "body": "See https://mycompany.atlassian.net/browse/DATA-789 for details",
        }
        result = detect_jira(email)
        assert len(result.tickets) >= 1
        ticket = next(t for t in result.tickets if t.key == "DATA-789")
        assert ticket.url is not None
        assert "DATA-789" in ticket.url

    def test_detects_multiple_tickets(self):
        email = {
            "sender": "jira@atlassian.net",
            "subject": "[JIRA] (API-100) Linked to API-200",
            "body": "Also related: API-300",
        }
        result = detect_jira(email)
        keys = {t.key for t in result.tickets}
        assert "API-100" in keys
        assert "API-200" in keys
        assert "API-300" in keys

    def test_no_jira_in_regular_email(self):
        email = {
            "sender": "alice@gmail.com",
            "subject": "Lunch tomorrow?",
            "body": "Are you free for lunch?",
        }
        result = detect_jira(email)
        assert not result.is_jira_email
        assert result.confidence < 0.4
        assert len(result.tickets) == 0

    def test_deduplicates_tickets(self):
        email = {
            "sender": "jira@company.com",
            "subject": "[JIRA] (PROJ-123) Title",
            "body": "Details about PROJ-123 at https://jira.co/browse/PROJ-123",
        }
        result = detect_jira(email)
        keys = [t.key for t in result.tickets]
        assert keys.count("PROJ-123") == 1

    def test_confidence_high_for_strong_signals(self):
        email = {
            "sender": "jira@atlassian.net",
            "subject": "[JIRA] (PROJ-123) Task assigned",
            "body": "",
        }
        result = detect_jira(email)
        assert result.confidence >= 0.8

    def test_confidence_low_for_body_only_ticket(self):
        email = {
            "sender": "alice@gmail.com",
            "subject": "Random email",
            "body": "Maybe check PROJ-123?",
        }
        result = detect_jira(email)
        assert result.confidence < 0.4

    def test_uses_snippet_as_fallback(self):
        email = {
            "sender": "jira@company.com",
            "subject": "Notification",
            "body": "",
            "snippet": "PROJ-999 has been updated",
        }
        result = detect_jira(email)
        assert any(t.key == "PROJ-999" for t in result.tickets)


class TestExtractTicketKeys:
    def test_extracts_single_key(self):
        assert extract_ticket_keys("Fix PROJ-123 asap") == ["PROJ-123"]

    def test_extracts_multiple_keys(self):
        keys = extract_ticket_keys("PROJ-1, PROJ-2, and DATA-99")
        assert keys == ["PROJ-1", "PROJ-2", "DATA-99"]

    def test_deduplicates(self):
        keys = extract_ticket_keys("PROJ-1 mentioned twice: PROJ-1")
        assert keys == ["PROJ-1"]

    def test_no_keys(self):
        assert extract_ticket_keys("No tickets here") == []

    def test_rejects_short_project_prefix(self):
        assert extract_ticket_keys("A-123") == []  # min 2 chars


# ── Classifier ─────────────────────────────────────────────────────────


class TestClassifier:
    def test_detects_assignment_in_subject(self):
        email = {"subject": "PROJ-123 has been assigned to you", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.ASSIGNED
        assert result.priority_hint == "high"

    def test_detects_comment(self):
        email = {"subject": "John added a comment on PROJ-123", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.COMMENT

    def test_detects_status_change(self):
        email = {"subject": "Status changed for PROJ-123", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.STATUS_CHANGE

    def test_detects_review_request(self):
        email = {"subject": "Review requested on PROJ-123", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.REVIEW_REQUESTED
        assert result.priority_hint == "high"

    def test_detects_resolved(self):
        email = {"subject": "PROJ-123 resolved", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.RESOLVED

    def test_detects_mention(self):
        email = {"subject": "Alice mentioned you on PROJ-123", "body": "", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.MENTIONED

    def test_falls_back_to_body(self):
        email = {
            "subject": "Notification",
            "body": "This task has been assigned to you",
            "snippet": "",
        }
        result = classify_email(email)
        assert result.action == EmailAction.ASSIGNED

    def test_unknown_for_unmatched(self):
        email = {"subject": "Hello world", "body": "Just saying hi", "snippet": ""}
        result = classify_email(email)
        assert result.action == EmailAction.UNKNOWN

    def test_subject_takes_priority_over_body(self):
        email = {
            "subject": "PROJ-123 has been assigned to you",
            "body": "John added a comment",
            "snippet": "",
        }
        result = classify_email(email)
        assert result.action == EmailAction.ASSIGNED


# ── Processor ──────────────────────────────────────────────────────────


class TestProcessor:
    def _make_jira_email(
        self, key="PROJ-123", action_text="assigned to you"
    ) -> dict:
        return {
            "id": "msg-001",
            "thread_id": "thread-001",
            "subject": f"[JIRA] ({key}) {action_text}",
            "sender": "jira@atlassian.net",
            "date": "2026-03-12",
            "body": f"The ticket {key} details here.",
            "snippet": "",
        }

    def _make_regular_email(self) -> dict:
        return {
            "id": "msg-002",
            "thread_id": "thread-002",
            "subject": "Team lunch Friday",
            "sender": "alice@company.com",
            "date": "2026-03-12",
            "body": "Who wants to join?",
            "snippet": "",
        }

    def test_process_jira_email(self):
        email = self._make_jira_email()
        result = process_email(email)
        assert result.jira.is_jira_email
        assert len(result.tickets) == 1
        assert result.tickets[0].key == "PROJ-123"
        assert result.classification.action == EmailAction.ASSIGNED
        assert result.requires_action

    def test_process_regular_email(self):
        email = self._make_regular_email()
        result = process_email(email)
        assert not result.jira.is_jira_email
        assert not result.requires_action
        assert "Non-Jira" in result.summary

    def test_requires_action_for_assignment(self):
        email = self._make_jira_email(action_text="assigned to you")
        result = process_email(email)
        assert result.requires_action

    def test_no_action_for_status_change(self):
        email = self._make_jira_email(action_text="status changed to Done")
        result = process_email(email)
        assert not result.requires_action

    def test_requires_action_for_review_request(self):
        email = self._make_jira_email(action_text="review requested")
        result = process_email(email)
        assert result.requires_action

    def test_summary_contains_ticket_key(self):
        email = self._make_jira_email(key="DATA-456")
        result = process_email(email)
        assert "DATA-456" in result.summary

    def test_summary_action_required_prefix(self):
        email = self._make_jira_email(action_text="assigned to you")
        result = process_email(email)
        assert "[ACTION REQUIRED]" in result.summary


class TestInboxProcessing:
    def _make_emails(self) -> list[dict]:
        return [
            {
                "id": "msg-1",
                "thread_id": "t-1",
                "subject": "[JIRA] (API-100) assigned to you",
                "sender": "jira@atlassian.net",
                "date": "2026-03-12",
                "body": "",
                "snippet": "",
            },
            {
                "id": "msg-2",
                "thread_id": "t-2",
                "subject": "[JIRA] (API-200) status changed",
                "sender": "jira@atlassian.net",
                "date": "2026-03-12",
                "body": "",
                "snippet": "",
            },
            {
                "id": "msg-3",
                "thread_id": "t-3",
                "subject": "[JIRA] (DATA-50) mentioned you",
                "sender": "jira@atlassian.net",
                "date": "2026-03-12",
                "body": "",
                "snippet": "",
            },
            {
                "id": "msg-4",
                "thread_id": "t-4",
                "subject": "Lunch?",
                "sender": "bob@company.com",
                "date": "2026-03-12",
                "body": "Let's eat",
                "snippet": "",
            },
        ]

    def test_counts_totals(self):
        summary = process_inbox(self._make_emails())
        assert summary.total_emails == 4
        assert summary.jira_emails == 3

    def test_action_required_filtered(self):
        summary = process_inbox(self._make_emails())
        action_ids = {a.email_id for a in summary.action_required}
        assert "msg-1" in action_ids  # assigned
        assert "msg-3" in action_ids  # mentioned
        assert "msg-2" not in action_ids  # status change

    def test_tickets_mentioned_deduplicated(self):
        summary = process_inbox(self._make_emails())
        keys = {t.key for t in summary.tickets_mentioned}
        assert "API-100" in keys
        assert "API-200" in keys
        assert "DATA-50" in keys

    def test_by_project_grouping(self):
        summary = process_inbox(self._make_emails())
        assert summary.by_project.get("API") == 2
        assert summary.by_project.get("DATA") == 1

    def test_by_action_distribution(self):
        summary = process_inbox(self._make_emails())
        assert summary.by_action.get("assigned") == 1
        assert summary.by_action.get("mentioned") == 1

    def test_empty_inbox(self):
        summary = process_inbox([])
        assert summary.total_emails == 0
        assert summary.jira_emails == 0
        assert len(summary.action_required) == 0
