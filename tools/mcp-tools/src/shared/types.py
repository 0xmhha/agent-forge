"""Shared type definitions for the agent-forge tool platform."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field, SecretStr


class ToolSource(StrEnum):
    GMAIL = "gmail"
    GITHUB = "github"


class TaskType(StrEnum):
    ISSUE = "issue"
    PR = "pr"
    CI_FAILURE = "ci_failure"
    EMAIL = "email"


class TaskStatus(StrEnum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    RESOLVED = "resolved"
    CLOSED = "closed"


class TaskPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class ToolResult(BaseModel):
    """Standard response from any MCP tool — never contains auth tokens."""

    success: bool
    data: dict[str, Any] = Field(default_factory=dict)
    error: str | None = None


class ToolRegistration(BaseModel):
    """Metadata for registering a tool module with the MCP server."""

    name: str
    source: ToolSource
    description: str
    version: str = "0.1.0"


class AuthConfig(BaseModel):
    """OAuth/API key configuration for a service — never exposed to LLM."""

    service: ToolSource
    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    token_path: str = ""
    scopes: list[str] = Field(default_factory=list)
    api_key: SecretStr = SecretStr("")


class ServiceHealth(BaseModel):
    """Health check result for a registered service."""

    service: ToolSource
    connected: bool
    last_checked: datetime
    error: str | None = None
