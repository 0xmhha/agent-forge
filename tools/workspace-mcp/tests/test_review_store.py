"""Tests for review file storage (pending/done/todo)."""

import pytest

from github.review.models import ReviewRequest
from github.review.store import ReviewStore


@pytest.fixture
def store(tmp_dir):
    return ReviewStore(base_dir=tmp_dir / "reviews")


@pytest.fixture
def sample_review():
    return ReviewRequest(
        repo="owner/my-repo",
        pr_number=42,
        pr_title="Fix authentication timeout",
        pr_url="https://github.com/owner/my-repo/pull/42",
        requester="alice",
        email_id="msg-001",
        email_subject="Review requested",
        head_branch="fix/auth",
        base_branch="main",
        pr_body="Fixes timeout issue",
        files=[
            {"filename": "auth.py", "status": "modified", "additions": 10, "deletions": 3}
        ],
        additions=10,
        deletions=3,
    )


class TestSavePending:
    def test_creates_pending_file(self, store, sample_review):
        path = store.save_pending(sample_review)

        assert path.exists()
        assert "pending" in str(path)
        assert path.suffix == ".md"

    def test_skips_existing_pending(self, store, sample_review):
        first = store.save_pending(sample_review)
        second = store.save_pending(sample_review)

        assert first == second

    def test_content_contains_pr_info(self, store, sample_review):
        path = store.save_pending(sample_review)
        content = path.read_text()

        assert "owner/my-repo" in content
        assert "42" in content


class TestSaveTodo:
    def test_creates_todo_file(self, store, sample_review):
        path = store.save_todo(sample_review)

        assert path.exists()
        assert "todo" in str(path)

    def test_todo_contains_review_commands(self, store, sample_review):
        path = store.save_todo(sample_review)
        content = path.read_text()

        assert "owner/my-repo" in content


class TestMarkDone:
    def test_moves_pending_to_done(self, store, sample_review):
        store.save_pending(sample_review)
        slug = sample_review.slug
        result = store.mark_done(slug)

        assert result is True
        assert len(store.list_done()) == 1
        assert len(store.list_pending()) == 0

    def test_returns_false_for_nonexistent(self, store):
        result = store.mark_done("nonexistent-slug")

        assert result is False


class TestListOperations:
    def test_list_pending_returns_reviews(self, store, sample_review):
        store.save_pending(sample_review)
        pending = store.list_pending()

        assert len(pending) == 1
        assert pending[0]["filename"].endswith(".md")

    def test_list_empty_returns_empty(self, store):
        assert store.list_pending() == []
        assert store.list_done() == []
        assert store.list_todo() == []


class TestHasPending:
    def test_detects_existing_review(self, store, sample_review):
        store.save_pending(sample_review)

        assert store.has_pending("owner/my-repo", 42) is True

    def test_returns_false_for_new_review(self, store):
        assert store.has_pending("owner/other-repo", 99) is False

    def test_detects_done_review(self, store, sample_review):
        store.save_pending(sample_review)
        store.mark_done(sample_review.slug)

        assert store.has_pending("owner/my-repo", 42) is True
