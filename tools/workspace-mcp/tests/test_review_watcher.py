"""Tests for GitHubReviewWatcher batch process."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from github.review.detector import ReviewDetectionResult
from github.review.store import ReviewStore
from github.review.watcher import GitHubReviewWatcher


@pytest.fixture
def review_store(tmp_path: Path):
    return ReviewStore(base_dir=tmp_path / "reviews")


@pytest.fixture
def gmail_client():
    return AsyncMock()


@pytest.fixture
def github_client():
    return AsyncMock()


@pytest.fixture
def watcher(gmail_client, github_client, review_store):
    return GitHubReviewWatcher(
        gmail_client=gmail_client,
        github_client=github_client,
        store=review_store,
    )


def _make_email_meta(msg_id: str = "msg-001") -> dict:
    return {"id": msg_id, "thread_id": "t-001", "subject": "review request"}


def _make_full_email(
    msg_id: str = "msg-001",
    sender: str = "notifications@github.com",
    subject: str = "Re: [owner/repo] fix: something (PR #42)",
    body: str = "@user requested your review on: owner/repo#42",
) -> dict:
    return {
        "id": msg_id,
        "thread_id": "t-001",
        "sender": sender,
        "subject": subject,
        "body": body,
        "snippet": body[:50],
    }


def _make_pr_data() -> dict:
    return {
        "title": "fix: something",
        "url": "https://github.com/owner/repo/pull/42",
        "body": "Fixes a bug",
        "head_branch": "fix/something",
        "base_branch": "main",
        "changed_files": 2,
        "additions": 10,
        "deletions": 3,
        "files": [{"filename": "src/foo.py", "status": "modified", "additions": 10, "deletions": 3}],
    }


def _make_detection(is_review: bool = True, repo: str = "owner/repo", pr: int = 42) -> ReviewDetectionResult:
    return ReviewDetectionResult(
        is_review_request=is_review,
        confidence=0.9 if is_review else 0.1,
        signals=["github_sender", "review_subject"] if is_review else [],
        repo=repo if is_review else "",
        pr_number=pr if is_review else 0,
        requester="someone",
        pr_url=f"https://github.com/{repo}/pull/{pr}" if is_review else "",
    )


class TestRunOnce:
    @pytest.mark.asyncio
    async def test_saves_pending_and_todo(self, watcher, gmail_client, github_client, review_store):
        gmail_client.list_messages.return_value = [_make_email_meta()]
        gmail_client.read_message.return_value = _make_full_email()
        github_client.get_pr.return_value = _make_pr_data()

        with patch("github.review.watcher.detect_review_request", return_value=_make_detection()):
            await watcher.run_once()

        pending = review_store.list_pending()
        todo = review_store.list_todo()
        assert len(pending) == 1
        assert len(todo) == 1
        assert "owner-repo-42" in pending[0]["filename"]
        assert "newjob-owner-repo-42" in todo[0]["filename"]

    @pytest.mark.asyncio
    async def test_skips_non_review_emails(self, watcher, gmail_client, github_client, review_store):
        gmail_client.list_messages.return_value = [_make_email_meta()]
        gmail_client.read_message.return_value = _make_full_email(subject="Regular notification")

        with patch("github.review.watcher.detect_review_request", return_value=_make_detection(is_review=False)):
            await watcher.run_once()

        assert len(review_store.list_pending()) == 0
        assert len(review_store.list_todo()) == 0

    @pytest.mark.asyncio
    async def test_skips_duplicate(self, watcher, gmail_client, github_client, review_store):
        gmail_client.list_messages.return_value = [_make_email_meta("m1"), _make_email_meta("m2")]
        gmail_client.read_message.return_value = _make_full_email()
        github_client.get_pr.return_value = _make_pr_data()

        with patch("github.review.watcher.detect_review_request", return_value=_make_detection()):
            await watcher.run_once()

        # Same repo/PR detected twice, but only one should be saved
        assert len(review_store.list_pending()) == 1
        assert len(review_store.list_todo()) == 1

    @pytest.mark.asyncio
    async def test_handles_api_error_continues(self, watcher, gmail_client, github_client, review_store):
        email1 = _make_email_meta("m1")
        email2 = _make_email_meta("m2")
        gmail_client.list_messages.return_value = [email1, email2]

        # First email fails, second succeeds
        call_count = 0

        async def read_side_effect(msg_id):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.HTTPStatusError(
                    "Server Error",
                    request=httpx.Request("GET", "https://example.com"),
                    response=httpx.Response(500),
                )
            return _make_full_email(msg_id=msg_id)

        gmail_client.read_message.side_effect = read_side_effect
        github_client.get_pr.return_value = _make_pr_data()

        with patch("github.review.watcher.detect_review_request", return_value=_make_detection()):
            await watcher.run_once()

        # Second email should still be processed
        assert len(review_store.list_pending()) == 1

    @pytest.mark.asyncio
    async def test_rate_limit_stops_early(self, watcher, gmail_client, github_client, review_store):
        gmail_client.list_messages.return_value = [_make_email_meta("m1"), _make_email_meta("m2")]

        gmail_client.read_message.side_effect = httpx.HTTPStatusError(
            "Rate Limited",
            request=httpx.Request("GET", "https://example.com"),
            response=httpx.Response(429),
        )

        await watcher.run_once()

        # Should stop after first 429, no pending/todo created
        assert len(review_store.list_pending()) == 0
        assert gmail_client.read_message.call_count == 1

    @pytest.mark.asyncio
    async def test_missing_repo_skipped(self, watcher, gmail_client, github_client, review_store):
        gmail_client.list_messages.return_value = [_make_email_meta()]
        gmail_client.read_message.return_value = _make_full_email()

        detection = ReviewDetectionResult(
            is_review_request=True,
            confidence=0.8,
            signals=["github_sender"],
            repo="",
            pr_number=0,
            requester="someone",
            pr_url="",
        )
        with patch("github.review.watcher.detect_review_request", return_value=detection):
            await watcher.run_once()

        assert len(review_store.list_pending()) == 0


class TestHasTodo:
    def test_has_todo_returns_false_when_empty(self, review_store):
        assert not review_store.has_todo("owner/repo", 42)

    def test_has_todo_returns_true_after_save(self, review_store):
        from github.review.models import ReviewRequest

        review = ReviewRequest(repo="owner/repo", pr_number=42, pr_title="test")
        review_store.save_todo(review)
        assert review_store.has_todo("owner/repo", 42)

    def test_has_pending_checks_todo_folder(self, review_store):
        from github.review.models import ReviewRequest

        review = ReviewRequest(repo="owner/repo", pr_number=42, pr_title="test")
        review_store.save_todo(review)
        # has_pending should also find items in todo folder
        assert review_store.has_pending("owner/repo", 42)
