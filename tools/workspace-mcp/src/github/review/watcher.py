"""GitHub review request watcher — batch process that scans Gmail periodically.

Detects PR review request emails, fetches PR details from GitHub API,
and saves structured review documents (pending + todo) to the file store.
"""

import logging
from typing import Any

import httpx

from github.client import GitHubClient
from github.review.detector import detect_review_request
from github.review.models import ReviewRequest
from github.review.store import ReviewStore
from gmail.client import GmailClient
from shared.events import EventDispatcher, ReviewDetected

logger = logging.getLogger(__name__)

_GMAIL_QUERY = 'from:notifications@github.com subject:"review requested"'


class GitHubReviewWatcher:
    """Watches Gmail for GitHub PR review requests and stores them."""

    def __init__(
        self,
        gmail_client: GmailClient,
        github_client: GitHubClient,
        store: ReviewStore | None = None,
        dispatcher: EventDispatcher | None = None,
    ) -> None:
        self._gmail = gmail_client
        self._github = github_client
        self._store = store or ReviewStore()
        self._dispatcher = dispatcher

    @property
    def name(self) -> str:
        return "github_review"

    async def run_once(self) -> int:
        """Scan Gmail for new review requests, save pending and todo files.

        Returns the number of new review requests found.
        """
        logger.info("Scanning Gmail for review requests...")

        emails = await self._gmail.list_messages(query=_GMAIL_QUERY, max_results=20)
        new_count = 0

        for email_meta in emails:
            try:
                new = await self._process_email(email_meta)
                if new:
                    new_count += 1
            except httpx.HTTPStatusError as exc:
                if exc.response.status_code == 429:
                    logger.warning("Rate limited, stopping scan early")
                    break
                logger.warning("Failed to process email %s: %s", email_meta.get("id"), exc)
            except Exception:
                logger.exception("Unexpected error processing email %s", email_meta.get("id"))

        logger.info("Scan complete: %d new review request(s) found", new_count)
        return new_count

    async def _process_email(self, email_meta: dict[str, Any]) -> bool:
        """Process a single email. Returns True if a new review was saved."""
        full_email = await self._gmail.read_message(email_meta["id"])
        detection = detect_review_request(full_email)

        if not detection.is_review_request:
            return False

        if not detection.repo or not detection.pr_number:
            logger.warning("Review detected but missing repo/PR: %s", full_email.get("subject"))
            return False

        if self._store.has_pending(detection.repo, detection.pr_number):
            logger.debug("Already tracked: %s#%d", detection.repo, detection.pr_number)
            return False

        review = await self._build_review_request(detection, full_email)
        self._store.save_pending(review)
        self._store.save_todo(review)
        logger.info("New review request + todo: %s#%d", review.repo, review.pr_number)

        if self._dispatcher:
            await self._dispatcher.dispatch(ReviewDetected(
                repo=review.repo,
                pr_number=review.pr_number,
                pr_title=review.pr_title,
                pr_url=review.pr_url,
                requester=review.requester,
                todo_filename=f"newjob-{review.slug}.md",
            ))

        return True

    async def _build_review_request(
        self,
        detection: Any,
        email: dict[str, Any],
    ) -> ReviewRequest:
        """Fetch PR details from GitHub and build a ReviewRequest."""
        pr_data: dict[str, Any] = {}
        try:
            pr_data = await self._github.get_pr(detection.repo, detection.pr_number)
        except Exception:
            logger.warning(
                "Failed to fetch PR details for %s#%d, saving with email data only",
                detection.repo,
                detection.pr_number,
            )

        return ReviewRequest(
            repo=detection.repo,
            pr_number=detection.pr_number,
            pr_title=pr_data.get("title", email.get("subject", "")),
            pr_url=detection.pr_url or pr_data.get("url", ""),
            pr_body=pr_data.get("body", ""),
            requester=detection.requester,
            head_branch=pr_data.get("head_branch", ""),
            base_branch=pr_data.get("base_branch", ""),
            changed_files=pr_data.get("changed_files", 0),
            additions=pr_data.get("additions", 0),
            deletions=pr_data.get("deletions", 0),
            files=pr_data.get("files", []),
            email_id=email.get("id", ""),
            email_subject=email.get("subject", ""),
        )
