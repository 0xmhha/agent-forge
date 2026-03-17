"""Batch watcher configuration — JSON file-based, shared between Setup UI and MCP server."""

import json
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

_DEFAULT_CONFIG_DIR = Path.home() / ".agent-forge"
_CONFIG_FILENAME = "batch-config.json"


class WatcherConfig(BaseModel):
    """Configuration for a single watcher."""

    enabled: bool = True
    interval_minutes: int = 10


class BatchConfig(BaseModel):
    """Top-level batch configuration with per-watcher settings."""

    watchers: dict[str, WatcherConfig] = Field(default_factory=lambda: {
        "github_review": WatcherConfig(),
    })

    def get_watcher(self, name: str) -> WatcherConfig:
        return self.watchers.get(name, WatcherConfig())


def load_batch_config(config_dir: Path | None = None) -> BatchConfig:
    """Load batch config from JSON file. Returns defaults if not found."""
    path = _config_path(config_dir)
    if not path.exists():
        return BatchConfig()
    try:
        raw = json.loads(path.read_text())
        return BatchConfig.model_validate(raw)
    except (json.JSONDecodeError, ValueError):
        return BatchConfig()


def save_batch_config(config: BatchConfig, config_dir: Path | None = None) -> None:
    """Save batch config to JSON file."""
    path = _config_path(config_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(config.model_dump_json(indent=2))


def update_watcher_config(
    name: str,
    *,
    enabled: bool | None = None,
    interval_minutes: int | None = None,
    config_dir: Path | None = None,
) -> BatchConfig:
    """Update a single watcher's config and save."""
    config = load_batch_config(config_dir)
    current = config.get_watcher(name)

    updated = WatcherConfig(
        enabled=enabled if enabled is not None else current.enabled,
        interval_minutes=interval_minutes if interval_minutes is not None else current.interval_minutes,
    )
    config = BatchConfig(
        watchers={**config.watchers, name: updated},
    )
    save_batch_config(config, config_dir)
    return config


def _config_path(config_dir: Path | None) -> Path:
    base = config_dir or _DEFAULT_CONFIG_DIR
    return base / _CONFIG_FILENAME
