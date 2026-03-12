"""Email processor — chains detection and classification rules.

This is the main entry point for rule-based email processing.
Takes raw email data from GmailClient and produces structured,
actionable results for the LLM to consume.
"""

from typing import Any

from pydantic import BaseModel

from gmail.rules.classifier import ClassificationResult, EmailAction, classify_email
from gmail.rules.jira_detector import JiraDetectionResult, JiraTicket, detect_jira


class ProcessedEmail(BaseModel):
    """Fully processed email with Jira detection and classification."""

    email_id: str
    thread_id: str
    subject: str
    sender: str
    date: str
    jira: JiraDetectionResult
    classification: ClassificationResult
    tickets: list[JiraTicket]
    requires_action: bool
    summary: str


class InboxSummary(BaseModel):
    """Aggregated summary of processed inbox emails."""

    total_emails: int
    jira_emails: int
    action_required: list[ProcessedEmail]
    tickets_mentioned: list[JiraTicket]
    by_action: dict[str, int]
    by_project: dict[str, int]


_ACTIONABLE_TYPES = frozenset({
    EmailAction.ASSIGNED,
    EmailAction.REVIEW_REQUESTED,
    EmailAction.MENTIONED,
})


def process_email(email: dict[str, Any]) -> ProcessedEmail:
    """Process a single email through the full rule pipeline.

    1. Detect Jira ticket references
    2. Classify the email action type
    3. Determine if action is required
    4. Generate a structured summary
    """
    jira_result = detect_jira(email)
    classification = classify_email(email) if jira_result.is_jira_email else ClassificationResult(
        action=EmailAction.UNKNOWN, matched_pattern="", priority_hint="low"
    )

    requires_action = (
        jira_result.is_jira_email
        and classification.action in _ACTIONABLE_TYPES
    )

    summary = _build_summary(email, jira_result, classification, requires_action)

    return ProcessedEmail(
        email_id=email.get("id", ""),
        thread_id=email.get("thread_id", ""),
        subject=email.get("subject", ""),
        sender=email.get("sender", ""),
        date=email.get("date", ""),
        jira=jira_result,
        classification=classification,
        tickets=jira_result.tickets,
        requires_action=requires_action,
        summary=summary,
    )


def process_inbox(emails: list[dict[str, Any]]) -> InboxSummary:
    """Process a batch of emails and produce an aggregated summary.

    Returns structured data optimized for LLM consumption:
    - Action-required emails highlighted
    - Tickets grouped by project
    - Action type distribution
    """
    processed = [process_email(email) for email in emails]

    jira_emails = [p for p in processed if p.jira.is_jira_email]
    action_required = [p for p in processed if p.requires_action]

    all_tickets: dict[str, JiraTicket] = {}
    for p in jira_emails:
        for ticket in p.tickets:
            all_tickets[ticket.key] = ticket

    by_action: dict[str, int] = {}
    for p in jira_emails:
        action = p.classification.action
        by_action[action] = by_action.get(action, 0) + 1

    by_project: dict[str, int] = {}
    for ticket in all_tickets.values():
        by_project[ticket.project] = by_project.get(ticket.project, 0) + 1

    return InboxSummary(
        total_emails=len(emails),
        jira_emails=len(jira_emails),
        action_required=action_required,
        tickets_mentioned=list(all_tickets.values()),
        by_action=by_action,
        by_project=by_project,
    )


def _build_summary(
    email: dict[str, Any],
    jira: JiraDetectionResult,
    classification: ClassificationResult,
    requires_action: bool,
) -> str:
    """Build a concise human-readable summary line."""
    if not jira.is_jira_email:
        return f"Non-Jira email: {email.get('subject', '(no subject)')}"

    ticket_keys = ", ".join(t.key for t in jira.tickets) or "unknown"
    action_label = classification.action.value.replace("_", " ")
    prefix = "[ACTION REQUIRED] " if requires_action else ""

    return f"{prefix}[{ticket_keys}] {action_label}: {email.get('subject', '')}"
