"""Tests for trigger file hooks."""

import json
from pathlib import Path

import pytest

from shared.events import BatchCycleFinished, ReviewCompleted, ReviewDetected
from shared.hooks import TriggerFileHook


@pytest.fixture
def hook(tmp_path: Path):
    return TriggerFileHook(triggers_dir=tmp_path / "triggers")


@pytest.fixture
def sample_review_detected():
    return ReviewDetected(
        repo="owner/repo",
        pr_number=42,
        pr_title="fix: something",
        pr_url="https://github.com/owner/repo/pull/42",
        requester="someone",
        todo_filename="newjob-owner-repo-42-20260317.md",
    )


class TestOnReviewDetected:
    @pytest.mark.asyncio
    async def test_creates_trigger_file(self, hook, sample_review_detected):
        await hook.on_review_detected(sample_review_detected)

        triggers = hook.list_pending_triggers()
        assert len(triggers) == 1
        assert triggers[0]["type"] == "review_detected"
        assert triggers[0]["action"] == "start_review"
        assert triggers[0]["repo"] == "owner/repo"
        assert triggers[0]["pr_number"] == 42

    @pytest.mark.asyncio
    async def test_trigger_filename_format(self, hook, sample_review_detected):
        await hook.on_review_detected(sample_review_detected)

        triggers = hook.list_pending_triggers()
        assert triggers[0]["_trigger_file"] == "review-owner-repo-42.json"


class TestOnReviewCompleted:
    @pytest.mark.asyncio
    async def test_moves_trigger_to_processed(self, hook, sample_review_detected):
        await hook.on_review_detected(sample_review_detected)
        assert len(hook.list_pending_triggers()) == 1

        completed = ReviewCompleted(repo="owner/repo", pr_number=42, slug="owner-repo-42-20260317")
        await hook.on_review_completed(completed)

        assert len(hook.list_pending_triggers()) == 0

        processed = list((hook._processed).glob("*.json"))
        assert len(processed) == 1
        data = json.loads(processed[0].read_text())
        assert data["type"] == "review_completed"

    @pytest.mark.asyncio
    async def test_no_pending_trigger_is_safe(self, hook):
        completed = ReviewCompleted(repo="owner/repo", pr_number=99, slug="owner-repo-99-20260317")
        await hook.on_review_completed(completed)  # should not raise


class TestOnBatchCycleFinished:
    @pytest.mark.asyncio
    async def test_creates_batch_trigger_when_new_items(self, hook):
        event = BatchCycleFinished(
            watcher_name="github_review", new_items=3, elapsed_seconds=1.5,
        )
        await hook.on_batch_cycle_finished(event)

        triggers = hook.list_pending_triggers()
        assert len(triggers) == 1
        assert triggers[0]["type"] == "batch_cycle_finished"
        assert triggers[0]["new_items"] == 3

    @pytest.mark.asyncio
    async def test_skips_trigger_when_no_new_items(self, hook):
        event = BatchCycleFinished(
            watcher_name="github_review", new_items=0, elapsed_seconds=0.5,
        )
        await hook.on_batch_cycle_finished(event)

        assert len(hook.list_pending_triggers()) == 0


class TestGetNextAction:
    @pytest.mark.asyncio
    async def test_returns_oldest_trigger(self, hook):
        event1 = ReviewDetected(
            repo="a/b", pr_number=1, pr_title="first",
            pr_url="", requester="x", todo_filename="f1.md",
        )
        event2 = ReviewDetected(
            repo="c/d", pr_number=2, pr_title="second",
            pr_url="", requester="y", todo_filename="f2.md",
        )
        await hook.on_review_detected(event1)
        await hook.on_review_detected(event2)

        action = hook.get_next_action()
        assert action is not None
        assert action["pr_number"] == 1

    def test_returns_none_when_empty(self, hook):
        assert hook.get_next_action() is None


class TestAcknowledgeTrigger:
    @pytest.mark.asyncio
    async def test_acknowledge_moves_to_processed(self, hook, sample_review_detected):
        await hook.on_review_detected(sample_review_detected)

        triggers = hook.list_pending_triggers()
        filename = triggers[0]["_trigger_file"]

        assert hook.acknowledge_trigger(filename)
        assert len(hook.list_pending_triggers()) == 0

        processed = list(hook._processed.glob("*.json"))
        assert len(processed) == 1
        data = json.loads(processed[0].read_text())
        assert data["acknowledged"] is True

    def test_acknowledge_nonexistent_returns_false(self, hook):
        assert not hook.acknowledge_trigger("nonexistent.json")
