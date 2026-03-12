"""Jira ticket detection from email content — pure rule-based, no LLM.

Detects Jira notification emails and extracts structured ticket data
from subjects, senders, and body text.
"""

import re
from typing import Any

from pydantic import BaseModel

# Jira ticket key: PROJECT-123 (2-10 uppercase letters + hyphen + digits)
_TICKET_KEY_RE = re.compile(r"\b([A-Z]{2,10}-\d+)\b")

# Common Jira notification sender patterns
_JIRA_SENDER_PATTERNS = [
    re.compile(r"jira@", re.IGNORECASE),
    re.compile(r"noreply@atlassian", re.IGNORECASE),
    re.compile(r"atlassian\.net", re.IGNORECASE),
    re.compile(r"jira\..*\.com", re.IGNORECASE),
    re.compile(r"no-?reply.*jira", re.IGNORECASE),
]

# Jira subject patterns: [JIRA] prefix or (PROJECT-123) pattern
_JIRA_SUBJECT_PREFIX_RE = re.compile(r"\[JIRA\]|\[jira\]")
_JIRA_SUBJECT_TICKET_RE = re.compile(r"\(([A-Z]{2,10}-\d+)\)")

# Jira URL patterns
_JIRA_URL_RE = re.compile(
    r"https?://[^\s]+/browse/([A-Z]{2,10}-\d+)"
    r"|https?://[^\s]+\.atlassian\.net/[^\s]*?([A-Z]{2,10}-\d+)"
)


class JiraTicket(BaseModel):
    """Structured Jira ticket data extracted from email."""

    key: str
    project: str
    url: str | None = None

    @staticmethod
    def from_key(key: str, url: str | None = None) -> "JiraTicket":
        project = key.rsplit("-", 1)[0]
        return JiraTicket(key=key, project=project, url=url)


class JiraDetectionResult(BaseModel):
    """Result of Jira detection on a single email."""

    is_jira_email: bool
    confidence: float  # 0.0 ~ 1.0
    tickets: list[JiraTicket]
    source_signals: list[str]  # which signals matched


def detect_jira(email: dict[str, Any]) -> JiraDetectionResult:
    """Detect Jira ticket references in an email using rule-based signals.

    Analyzes sender, subject, and body for Jira-related patterns.
    Returns structured detection result with confidence score.
    """
    signals: list[str] = []
    tickets_map: dict[str, JiraTicket] = {}

    subject = email.get("subject", "")
    sender = email.get("sender", "")
    body = email.get("body", "")
    snippet = email.get("snippet", "")

    # Signal 1: Sender is Jira system
    if _is_jira_sender(sender):
        signals.append("jira_sender")

    # Signal 2: Subject has [JIRA] prefix
    if _JIRA_SUBJECT_PREFIX_RE.search(subject):
        signals.append("jira_subject_prefix")

    # Signal 3: Subject contains (PROJECT-123) pattern
    subject_ticket_match = _JIRA_SUBJECT_TICKET_RE.search(subject)
    if subject_ticket_match:
        signals.append("jira_subject_ticket")
        key = subject_ticket_match.group(1)
        tickets_map[key] = JiraTicket.from_key(key)

    # Signal 4: Ticket keys in subject
    for match in _TICKET_KEY_RE.finditer(subject):
        key = match.group(1)
        if key not in tickets_map:
            signals.append("ticket_key_in_subject")
            tickets_map[key] = JiraTicket.from_key(key)

    # Signal 5: Jira URLs in body
    text_to_scan = f"{body}\n{snippet}"
    for match in _JIRA_URL_RE.finditer(text_to_scan):
        key = match.group(1) or match.group(2)
        if key:
            signals.append("jira_url_in_body")
            tickets_map[key] = JiraTicket.from_key(key, url=match.group(0))

    # Signal 6: Ticket keys in body (lower confidence on its own)
    for match in _TICKET_KEY_RE.finditer(text_to_scan):
        key = match.group(1)
        if key not in tickets_map:
            signals.append("ticket_key_in_body")
            tickets_map[key] = JiraTicket.from_key(key)

    confidence = _calculate_confidence(signals)
    unique_signals = list(dict.fromkeys(signals))

    return JiraDetectionResult(
        is_jira_email=confidence >= 0.4,
        confidence=confidence,
        tickets=list(tickets_map.values()),
        source_signals=unique_signals,
    )


def extract_ticket_keys(text: str) -> list[str]:
    """Extract all Jira ticket keys from arbitrary text."""
    return list(dict.fromkeys(_TICKET_KEY_RE.findall(text)))


def _is_jira_sender(sender: str) -> bool:
    return any(pattern.search(sender) for pattern in _JIRA_SENDER_PATTERNS)


def _calculate_confidence(signals: list[str]) -> float:
    """Calculate detection confidence from accumulated signals.

    Each signal contributes a weight. Signals compound but cap at 1.0.
    """
    weights = {
        "jira_sender": 0.5,
        "jira_subject_prefix": 0.5,
        "jira_subject_ticket": 0.3,
        "ticket_key_in_subject": 0.2,
        "jira_url_in_body": 0.3,
        "ticket_key_in_body": 0.1,
    }
    score = sum(weights.get(s, 0.0) for s in signals)
    return min(score, 1.0)
