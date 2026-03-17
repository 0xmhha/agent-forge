"""Async event dispatcher for workspace-mcp lifecycle events.

Provides a lightweight publish/subscribe system for decoupled communication
between components. Subscribers are async callables invoked when events fire.

Usage:
    dispatcher = EventDispatcher()
    dispatcher.subscribe(ReviewDetected, my_handler)
    await dispatcher.dispatch(ReviewDetected(repo="owner/repo", pr_number=42, ...))
"""

import logging
from collections import defaultdict
from collections.abc import Callable, Coroutine
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

logger = logging.getLogger(__name__)

EventHandler = Callable[..., Coroutine[Any, Any, None]]


# ── Event Types ──────────────────────────────────────────


@dataclass(frozen=True)
class ReviewDetected:
    """Fired when a new PR review request is discovered by the batch watcher."""

    repo: str
    pr_number: int
    pr_title: str
    pr_url: str
    requester: str
    todo_filename: str
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class ReviewCompleted:
    """Fired when a review is marked as done."""

    repo: str
    pr_number: int
    slug: str
    completed_at: str = field(default_factory=lambda: datetime.now().isoformat())


@dataclass(frozen=True)
class BatchCycleFinished:
    """Fired after a batch watcher completes one scan cycle."""

    watcher_name: str
    new_items: int
    elapsed_seconds: float
    finished_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ── Dispatcher ───────────────────────────────────────────


class EventDispatcher:
    """Async event dispatcher with type-based subscriber routing."""

    def __init__(self) -> None:
        self._subscribers: dict[type, list[EventHandler]] = defaultdict(list)

    def subscribe(self, event_type: type, handler: EventHandler) -> None:
        """Register a handler for an event type."""
        self._subscribers[event_type].append(handler)
        logger.debug("Event subscriber added: %s -> %s", event_type.__name__, handler.__name__)

    async def dispatch(self, event: Any) -> None:
        """Dispatch an event to all registered handlers for its type.

        Errors in individual handlers are logged but do not block other handlers.
        """
        event_type = type(event)
        handlers = self._subscribers.get(event_type, [])

        if not handlers:
            logger.debug("No handlers for event: %s", event_type.__name__)
            return

        logger.info("Dispatching %s to %d handler(s)", event_type.__name__, len(handlers))
        for handler in handlers:
            try:
                await handler(event)
            except Exception:
                logger.exception(
                    "Event handler %s failed for %s",
                    handler.__name__,
                    event_type.__name__,
                )

    @property
    def subscriber_count(self) -> int:
        return sum(len(hs) for hs in self._subscribers.values())
