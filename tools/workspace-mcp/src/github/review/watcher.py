"""GitHub review request watcher — batch process that scans Gmail periodically.

Detects PR review request emails, fetches PR details from GitHub API,
and saves structured review documents to the file store.
"""

import logging
from typing import Any

from github.client import GitHubClient
from github.review.detector import detect_review_request
from github.review.models import ReviewRequest
from github.review.store import ReviewStore
from gmail.client import GmailClient

logger = logging.getLogger(__name__)

_GMAIL_QUERY = 'from:notifications@github.com subject:"review requested"'


class GitHubReviewWatcher:
    """Watches Gmail for GitHub PR review requests and stores them."""

    def __init__(
        self,
        gmail_client: GmailClient,
        github_client: GitHubClient,
        store: ReviewStore | None = None,
    ) -> None:
        self._gmail = gmail_client
        self._github = github_client
        self._store = store or ReviewStore()

    @property
    def name(self) -> str:
        return "github_review"

    async def run_once(self) -> None:
        """Scan Gmail for new review requests and process them."""
        logger.info("Scanning Gmail for review requests...")

        emails = await self._gmail.list_messages(query=_GMAIL_QUERY, max_results=20)
        new_count = 0

        for email_meta in emails:
            full_email = await self._gmail.read_message(email_meta["id"])
            detection = detect_review_request(full_email)

            if not detection.is_review_request:
                continue

            if not detection.repo or not detection.pr_number:
                logger.warning("Review detected but missing repo/PR: %s", full_email.get("subject"))
                continue

            if self._store.has_pending(detection.repo, detection.pr_number):
                continue

            review = await self._build_review_request(detection, full_email)
            self._store.save_pending(review)
            new_count += 1
            logger.info("New review request: %s#%d", review.repo, review.pr_number)

        logger.info("Scan complete: %d new review request(s) found", new_count)

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
