"""GitHub review request detection from email — pure rule-based, no LLM.

Detects GitHub PR review request emails from Gmail and extracts
repo, PR number, and requester information.
"""

import re
from typing import Any

from pydantic import BaseModel

_GITHUB_SENDER_RE = re.compile(r"notifications@github\.com", re.IGNORECASE)

_REVIEW_SUBJECT_PATTERNS = [
    re.compile(r"review requested.*\[(.+?)#(\d+)\]", re.IGNORECASE),
    re.compile(r"\[(.+?)\]\s+.+?\s+#(\d+)", re.IGNORECASE),
]

_REVIEW_BODY_PATTERNS = [
    re.compile(r"requested your review on", re.IGNORECASE),
    re.compile(r"review requested", re.IGNORECASE),
    re.compile(r"please review", re.IGNORECASE),
]

_PR_URL_RE = re.compile(
    r"https?://github\.com/([^/]+/[^/]+)/pull/(\d+)"
)


class ReviewDetectionResult(BaseModel):
    """Result of GitHub review request detection on a single email."""

    is_review_request: bool
    repo: str = ""
    pr_number: int = 0
    requester: str = ""
    pr_url: str = ""
    confidence: float = 0.0
    signals: list[str] = []


def detect_review_request(email: dict[str, Any]) -> ReviewDetectionResult:
    """Detect GitHub PR review request in an email using rule-based signals."""
    signals: list[str] = []
    repo = ""
    pr_number = 0
    pr_url = ""

    subject = email.get("subject", "")
    sender = email.get("sender", "")
    body = email.get("body", "")
    snippet = email.get("snippet", "")
    text = f"{body}\n{snippet}"

    if not _GITHUB_SENDER_RE.search(sender):
        return ReviewDetectionResult(is_review_request=False)

    signals.append("github_sender")

    for pattern in _REVIEW_SUBJECT_PATTERNS:
        match = pattern.search(subject)
        if match:
            signals.append("review_subject")
            repo = repo or match.group(1)
            pr_number = pr_number or int(match.group(2))
            break

    for pattern in _REVIEW_BODY_PATTERNS:
        if pattern.search(text):
            signals.append("review_body")
            break

    url_match = _PR_URL_RE.search(text)
    if url_match:
        signals.append("pr_url")
        repo = repo or url_match.group(1)
        pr_number = pr_number or int(url_match.group(2))
        pr_url = url_match.group(0)

    if not url_match:
        url_match = _PR_URL_RE.search(subject)
        if url_match:
            signals.append("pr_url_in_subject")
            repo = repo or url_match.group(1)
            pr_number = pr_number or int(url_match.group(2))
            pr_url = url_match.group(0)

    requester = _extract_requester(sender, subject)
    confidence = _calculate_confidence(signals)

    return ReviewDetectionResult(
        is_review_request=confidence >= 0.5,
        repo=repo,
        pr_number=pr_number,
        requester=requester,
        pr_url=pr_url,
        confidence=confidence,
        signals=list(dict.fromkeys(signals)),
    )


def _extract_requester(sender: str, subject: str) -> str:
    """Extract the person who requested the review from email metadata."""
    name_match = re.match(r"^(.+?)\s*<", sender)
    if name_match:
        return name_match.group(1).strip()
    return ""


def _calculate_confidence(signals: list[str]) -> float:
    weights = {
        "github_sender": 0.3,
        "review_subject": 0.4,
        "review_body": 0.3,
        "pr_url": 0.3,
        "pr_url_in_subject": 0.3,
    }
    score = sum(weights.get(s, 0.0) for s in signals)
    return min(score, 1.0)
