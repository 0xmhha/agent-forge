"""Tests for the async event dispatcher."""

import pytest

from shared.events import (
    BatchCycleFinished,
    EventDispatcher,
    ReviewCompleted,
    ReviewDetected,
)


@pytest.fixture
def dispatcher():
    return EventDispatcher()


class TestEventDispatcher:
    @pytest.mark.asyncio
    async def test_dispatch_calls_subscriber(self, dispatcher):
        received = []

        async def handler(event):
            received.append(event)

        dispatcher.subscribe(ReviewDetected, handler)
        event = ReviewDetected(
            repo="owner/repo", pr_number=42, pr_title="fix",
            pr_url="https://github.com/owner/repo/pull/42",
            requester="someone", todo_filename="newjob-owner-repo-42-20260317.md",
        )
        await dispatcher.dispatch(event)

        assert len(received) == 1
        assert received[0].repo == "owner/repo"
        assert received[0].pr_number == 42

    @pytest.mark.asyncio
    async def test_dispatch_multiple_subscribers(self, dispatcher):
        calls = {"a": 0, "b": 0}

        async def handler_a(event):
            calls["a"] += 1

        async def handler_b(event):
            calls["b"] += 1

        dispatcher.subscribe(ReviewDetected, handler_a)
        dispatcher.subscribe(ReviewDetected, handler_b)

        event = ReviewDetected(
            repo="o/r", pr_number=1, pr_title="t",
            pr_url="", requester="x", todo_filename="f.md",
        )
        await dispatcher.dispatch(event)

        assert calls["a"] == 1
        assert calls["b"] == 1

    @pytest.mark.asyncio
    async def test_dispatch_wrong_type_not_called(self, dispatcher):
        called = False

        async def handler(event):
            nonlocal called
            called = True

        dispatcher.subscribe(ReviewDetected, handler)

        await dispatcher.dispatch(ReviewCompleted(repo="o/r", pr_number=1, slug="s"))
        assert not called

    @pytest.mark.asyncio
    async def test_handler_error_does_not_block_others(self, dispatcher):
        results = []

        async def failing_handler(event):
            raise RuntimeError("boom")

        async def working_handler(event):
            results.append("ok")

        dispatcher.subscribe(ReviewDetected, failing_handler)
        dispatcher.subscribe(ReviewDetected, working_handler)

        event = ReviewDetected(
            repo="o/r", pr_number=1, pr_title="t",
            pr_url="", requester="x", todo_filename="f.md",
        )
        await dispatcher.dispatch(event)

        assert results == ["ok"]

    @pytest.mark.asyncio
    async def test_dispatch_no_subscribers(self, dispatcher):
        # Should not raise
        event = ReviewDetected(
            repo="o/r", pr_number=1, pr_title="t",
            pr_url="", requester="x", todo_filename="f.md",
        )
        await dispatcher.dispatch(event)

    def test_subscriber_count(self, dispatcher):
        async def h(e): pass

        assert dispatcher.subscriber_count == 0
        dispatcher.subscribe(ReviewDetected, h)
        assert dispatcher.subscriber_count == 1
        dispatcher.subscribe(ReviewCompleted, h)
        assert dispatcher.subscriber_count == 2

    def test_batch_cycle_finished_event(self):
        event = BatchCycleFinished(
            watcher_name="github_review",
            new_items=3,
            elapsed_seconds=1.5,
        )
        assert event.watcher_name == "github_review"
        assert event.new_items == 3
