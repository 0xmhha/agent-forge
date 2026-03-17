"""Tests for GitHub review request detection from emails."""

import pytest

from github.review.detector import detect_review_request


class TestDetectReviewRequest:
    """detect_review_request should identify PR review emails from GitHub."""

    def _make_email(self, **overrides):
        base = {
            "id": "msg-001",
            "subject": "Re: [owner/repo] Fix auth timeout (#42)",
            "sender": "notifications@github.com",
            "body": "alice requested your review on https://github.com/owner/repo/pull/42",
            "snippet": "",
        }
        return {**base, **overrides}

    def test_detects_review_request_from_github_sender(self):
        email = self._make_email()
        result = detect_review_request(email)

        assert result.is_review_request is True
        assert result.repo == "owner/repo"
        assert result.pr_number == 42

    def test_rejects_non_github_sender(self):
        email = self._make_email(sender="alice@example.com")
        result = detect_review_request(email)

        assert result.is_review_request is False

    def test_extracts_repo_and_pr_from_url(self):
        email = self._make_email(
            body="Check https://github.com/my-org/my-repo/pull/123"
        )
        result = detect_review_request(email)

        assert result.repo == "my-org/my-repo"
        assert result.pr_number == 123

    def test_extracts_requester_from_sender_name(self):
        email = self._make_email(
            sender="Bob Smith <notifications@github.com>",
            body="requested your review on https://github.com/org/repo/pull/1",
        )
        result = detect_review_request(email)

        assert result.requester == "Bob Smith"

    def test_empty_requester_when_no_sender_name(self):
        email = self._make_email(sender="notifications@github.com")
        result = detect_review_request(email)

        assert result.requester == ""

    def test_confidence_high_for_multiple_signals(self):
        email = self._make_email(
            subject="[owner/repo] requested your review on #42",
            body="alice requested your review on https://github.com/owner/repo/pull/42",
        )
        result = detect_review_request(email)

        assert result.confidence >= 0.5

    def test_missing_pr_url_returns_no_detection(self):
        email = self._make_email(
            subject="Random GitHub notification",
            body="Something happened in the repo",
        )
        result = detect_review_request(email)

        assert result.is_review_request is False

    def test_empty_email_fields(self):
        email = self._make_email(subject="", body="", snippet="")
        result = detect_review_request(email)

        assert result.is_review_request is False

    def test_uses_snippet_as_fallback(self):
        email = self._make_email(
            body="",
            snippet="review requested https://github.com/org/repo/pull/99",
        )
        result = detect_review_request(email)

        assert result.pr_number == 99

    def test_pr_url_in_subject(self):
        email = self._make_email(
            subject="Review https://github.com/org/repo/pull/77",
            body="Please review",
        )
        result = detect_review_request(email)

        assert result.pr_number == 77
