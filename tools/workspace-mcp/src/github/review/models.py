"""Review request models and markdown document generation."""

from datetime import datetime

from pydantic import BaseModel, Field


class ReviewRequest(BaseModel):
    """A detected code review request with PR metadata."""

    repo: str
    pr_number: int
    pr_title: str = ""
    pr_url: str = ""
    pr_body: str = ""
    requester: str = ""
    head_branch: str = ""
    base_branch: str = ""
    changed_files: int = 0
    additions: int = 0
    deletions: int = 0
    files: list[dict] = Field(default_factory=list)
    detected_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    email_id: str = ""
    email_subject: str = ""

    @property
    def slug(self) -> str:
        """Filename-safe identifier: owner-repo-pr-date."""
        safe_repo = self.repo.replace("/", "-")
        date_str = datetime.now().strftime("%Y%m%d")
        return f"{safe_repo}-{self.pr_number}-{date_str}"

    def to_pending_markdown(self) -> str:
        """Generate markdown for pending review file."""
        files_section = _format_files(self.files)
        return f"""# Review Request: {self.repo}#{self.pr_number}

## Summary

| Field | Value |
|-------|-------|
| Repository | `{self.repo}` |
| PR | #{self.pr_number} |
| Title | {self.pr_title} |
| URL | {self.pr_url} |
| Requester | {self.requester} |
| Branch | `{self.head_branch}` -> `{self.base_branch}` |
| Changes | +{self.additions} -{self.deletions} ({self.changed_files} files) |
| Detected | {self.detected_at} |

## Description

{self.pr_body or "(no description)"}

## Changed Files

{files_section}

## Status

- [x] Detected
- [ ] Review started
- [ ] Review completed
"""

    def to_todo_markdown(self) -> str:
        """Generate agent-friendly todo document for review work."""
        files_section = _format_files(self.files)
        return f"""# TODO: Code Review — {self.repo}#{self.pr_number}

## Task

Review PR #{self.pr_number} in `{self.repo}`.

## Context

| Field | Value |
|-------|-------|
| Repository | `{self.repo}` |
| PR | #{self.pr_number} |
| Title | {self.pr_title} |
| URL | {self.pr_url} |
| Requester | {self.requester} |
| Branch | `{self.head_branch}` -> `{self.base_branch}` |
| Changes | +{self.additions} -{self.deletions} ({self.changed_files} files) |

## Setup Commands

```bash
# Clone and checkout PR branch
gh repo clone {self.repo} /tmp/review-{self.repo.replace("/", "-")}-{self.pr_number}
cd /tmp/review-{self.repo.replace("/", "-")}-{self.pr_number}
gh pr checkout {self.pr_number}

# View PR diff
gh pr diff {self.pr_number}

# View PR commits
gh pr view {self.pr_number} --comments
```

## Changed Files

{files_section}

## Review Checklist

- [ ] Clone repository and checkout PR branch
- [ ] Review changed files for correctness
- [ ] Check for security issues
- [ ] Check for test coverage
- [ ] Provide review feedback

## Status

- **Created**: {datetime.now().strftime("%Y-%m-%d %H:%M")}
- **Status**: pending
"""


def _format_files(files: list[dict]) -> str:
    if not files:
        return "(file list not available)"
    lines = []
    for f in files:
        status = f.get("status", "modified")
        name = f.get("filename", "")
        adds = f.get("additions", 0)
        dels = f.get("deletions", 0)
        lines.append(f"- `{name}` ({status}, +{adds} -{dels})")
    return "\n".join(lines)
