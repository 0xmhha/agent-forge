"""Email classification rules — categorizes Jira emails by action type.

Pure rule-based: pattern matching on subject and body text.
No LLM involvement — deterministic classification.
"""

import re
from enum import StrEnum
from typing import Any

from pydantic import BaseModel


class EmailAction(StrEnum):
    """Action types detected from Jira notification emails."""

    ASSIGNED = "assigned"
    COMMENT = "comment"
    STATUS_CHANGE = "status_change"
    CREATED = "created"
    MENTIONED = "mentioned"
    REVIEW_REQUESTED = "review_requested"
    RESOLVED = "resolved"
    UPDATED = "updated"
    UNKNOWN = "unknown"


# Pattern → action mapping (order matters: first match wins)
_ACTION_PATTERNS: list[tuple[re.Pattern, EmailAction]] = [
    (re.compile(r"assign(ed)?\s+(to\s+)?you", re.IGNORECASE), EmailAction.ASSIGNED),
    (re.compile(r"has been assigned to you", re.IGNORECASE), EmailAction.ASSIGNED),
    (re.compile(r"assigned .+ to you", re.IGNORECASE), EmailAction.ASSIGNED),
    (re.compile(r"mentioned you", re.IGNORECASE), EmailAction.MENTIONED),
    (re.compile(r"added a comment", re.IGNORECASE), EmailAction.COMMENT),
    (re.compile(r"commented on", re.IGNORECASE), EmailAction.COMMENT),
    (re.compile(r"new comment", re.IGNORECASE), EmailAction.COMMENT),
    (re.compile(r"requested.*review", re.IGNORECASE), EmailAction.REVIEW_REQUESTED),
    (re.compile(r"review requested", re.IGNORECASE), EmailAction.REVIEW_REQUESTED),
    (re.compile(r"resolved", re.IGNORECASE), EmailAction.RESOLVED),
    (re.compile(r"closed", re.IGNORECASE), EmailAction.RESOLVED),
    (re.compile(r"changed\s+(the\s+)?status", re.IGNORECASE), EmailAction.STATUS_CHANGE),
    (re.compile(r"transitioned", re.IGNORECASE), EmailAction.STATUS_CHANGE),
    (re.compile(r"moved to", re.IGNORECASE), EmailAction.STATUS_CHANGE),
    (re.compile(r"status changed", re.IGNORECASE), EmailAction.STATUS_CHANGE),
    (re.compile(r"created\s+(a\s+)?(new\s+)?issue", re.IGNORECASE), EmailAction.CREATED),
    (re.compile(r"new issue", re.IGNORECASE), EmailAction.CREATED),
    (re.compile(r"updated", re.IGNORECASE), EmailAction.UPDATED),
]


class ClassificationResult(BaseModel):
    """Classification output for a single email."""

    action: EmailAction
    matched_pattern: str
    priority_hint: str  # suggested priority based on action type


# Action → priority hint mapping
_PRIORITY_HINTS: dict[EmailAction, str] = {
    EmailAction.ASSIGNED: "high",
    EmailAction.REVIEW_REQUESTED: "high",
    EmailAction.MENTIONED: "medium",
    EmailAction.COMMENT: "medium",
    EmailAction.STATUS_CHANGE: "low",
    EmailAction.CREATED: "medium",
    EmailAction.RESOLVED: "low",
    EmailAction.UPDATED: "low",
    EmailAction.UNKNOWN: "low",
}


def classify_email(email: dict[str, Any]) -> ClassificationResult:
    """Classify a Jira email by action type using pattern matching.

    Scans subject first (higher signal), then body.
    Returns the first matching action type.
    """
    subject = email.get("subject", "")
    body = email.get("body", "")
    snippet = email.get("snippet", "")

    # Check subject first (stronger signal)
    for pattern, action in _ACTION_PATTERNS:
        if pattern.search(subject):
            return ClassificationResult(
                action=action,
                matched_pattern=pattern.pattern,
                priority_hint=_PRIORITY_HINTS[action],
            )

    # Then check body and snippet
    text = f"{body}\n{snippet}"
    for pattern, action in _ACTION_PATTERNS:
        if pattern.search(text):
            return ClassificationResult(
                action=action,
                matched_pattern=pattern.pattern,
                priority_hint=_PRIORITY_HINTS[action],
            )

    return ClassificationResult(
        action=EmailAction.UNKNOWN,
        matched_pattern="",
        priority_hint=_PRIORITY_HINTS[EmailAction.UNKNOWN],
    )
