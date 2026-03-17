"""Event hook subscribers that write trigger files for external agents.

When events fire, these hooks write JSON trigger files to data/triggers/.
External agents (Claude Code sessions, cron jobs) poll this directory
to discover new work and completed results.

Trigger file lifecycle:
    1. Event fires → hook writes trigger JSON
    2. External agent reads trigger → starts work
    3. Agent completes → deletes trigger or moves to processed/
"""

import json
import logging
from dataclasses import asdict
from pathlib import Path

from shared.events import BatchCycleFinished, ReviewCompleted, ReviewDetected

logger = logging.getLogger(__name__)

_DEFAULT_TRIGGERS_DIR = Path(__file__).resolve().parents[2] / "data" / "triggers"


class TriggerFileHook:
    """Writes JSON trigger files when review events occur."""

    def __init__(self, triggers_dir: Path | None = None) -> None:
        self._dir = triggers_dir or _DEFAULT_TRIGGERS_DIR
        self._pending = self._dir / "pending"
        self._processed = self._dir / "processed"
        for d in (self._pending, self._processed):
            d.mkdir(parents=True, exist_ok=True)

    async def on_review_detected(self, event: ReviewDetected) -> None:
        """Write a trigger file when a new review request is detected."""
        filename = f"review-{event.repo.replace('/', '-')}-{event.pr_number}.json"
        trigger = {
            "type": "review_detected",
            "action": "start_review",
            **asdict(event),
        }
        self._write_trigger(filename, trigger)
        logger.info("Trigger created: %s", filename)

    async def on_review_completed(self, event: ReviewCompleted) -> None:
        """Move trigger to processed when a review is completed."""
        filename = f"review-{event.repo.replace('/', '-')}-{event.pr_number}.json"
        src = self._pending / filename
        if src.exists():
            dst = self._processed / filename
            # Update trigger with completion info
            trigger = json.loads(src.read_text(encoding="utf-8"))
            trigger["type"] = "review_completed"
            trigger["completed_at"] = event.completed_at
            dst.write_text(json.dumps(trigger, indent=2), encoding="utf-8")
            src.unlink()
            logger.info("Trigger completed: %s", filename)
        else:
            logger.debug("No pending trigger to complete: %s", filename)

    async def on_batch_cycle_finished(self, event: BatchCycleFinished) -> None:
        """Write a summary trigger after batch cycle if new items found."""
        if event.new_items == 0:
            return
        filename = f"batch-{event.watcher_name}-{event.finished_at[:10]}.json"
        trigger = {
            "type": "batch_cycle_finished",
            "action": "check_new_reviews",
            **asdict(event),
        }
        self._write_trigger(filename, trigger)
        logger.info("Batch trigger created: %s (%d new items)", filename, event.new_items)

    def list_pending_triggers(self) -> list[dict]:
        """List all pending trigger files, sorted by modification time."""
        files = sorted(self._pending.glob("*.json"), key=lambda f: f.stat().st_mtime)
        results = []
        for f in files:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                data["_trigger_file"] = f.name
                results.append(data)
            except (json.JSONDecodeError, OSError):
                logger.warning("Failed to read trigger file: %s", f.name)
        return results

    def get_next_action(self) -> dict | None:
        """Return the oldest pending trigger, or None if queue is empty."""
        triggers = self.list_pending_triggers()
        return triggers[0] if triggers else None

    def acknowledge_trigger(self, filename: str) -> bool:
        """Move a trigger from pending to processed (agent picked it up)."""
        src = self._pending / filename
        if not src.exists():
            return False
        dst = self._processed / filename
        trigger = json.loads(src.read_text(encoding="utf-8"))
        trigger["acknowledged"] = True
        dst.write_text(json.dumps(trigger, indent=2), encoding="utf-8")
        src.unlink()
        logger.info("Trigger acknowledged: %s", filename)
        return True

    def _write_trigger(self, filename: str, data: dict) -> Path:
        path = self._pending / filename
        path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        return path
