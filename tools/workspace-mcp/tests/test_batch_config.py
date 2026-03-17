"""Tests for batch scheduler configuration."""

import json

import pytest

from shared.batch.config import (
    BatchConfig,
    WatcherConfig,
    load_batch_config,
    save_batch_config,
    update_watcher_config,
)


class TestWatcherConfig:
    def test_defaults(self):
        config = WatcherConfig()
        assert config.enabled is True
        assert config.interval_minutes == 10


class TestBatchConfig:
    def test_get_existing_watcher(self):
        config = BatchConfig(
            watchers={"github_review": WatcherConfig(enabled=False, interval_minutes=5)}
        )
        watcher = config.get_watcher("github_review")

        assert watcher.enabled is False
        assert watcher.interval_minutes == 5

    def test_get_nonexistent_returns_defaults(self):
        config = BatchConfig()
        watcher = config.get_watcher("unknown")

        assert watcher.enabled is True
        assert watcher.interval_minutes == 10


class TestLoadBatchConfig:
    def test_returns_defaults_when_no_file(self, tmp_dir):
        config = load_batch_config(config_dir=tmp_dir)

        assert isinstance(config, BatchConfig)

    def test_loads_from_json(self, tmp_dir):
        config_file = tmp_dir / "batch-config.json"
        config_file.write_text(json.dumps({
            "watchers": {
                "github_review": {"enabled": False, "interval_minutes": 30}
            }
        }))

        config = load_batch_config(config_dir=tmp_dir)
        watcher = config.get_watcher("github_review")

        assert watcher.enabled is False
        assert watcher.interval_minutes == 30

    def test_handles_invalid_json(self, tmp_dir):
        config_file = tmp_dir / "batch-config.json"
        config_file.write_text("not valid json{{{")

        config = load_batch_config(config_dir=tmp_dir)

        assert isinstance(config, BatchConfig)


class TestSaveBatchConfig:
    def test_saves_to_json(self, tmp_dir):
        config = BatchConfig(
            watchers={"test": WatcherConfig(enabled=False)}
        )
        save_batch_config(config, config_dir=tmp_dir)

        saved = json.loads((tmp_dir / "batch-config.json").read_text())
        assert saved["watchers"]["test"]["enabled"] is False

    def test_creates_directory(self, tmp_dir):
        nested = tmp_dir / "sub" / "dir"
        config = BatchConfig()
        save_batch_config(config, config_dir=nested)

        assert (nested / "batch-config.json").exists()


class TestUpdateWatcherConfig:
    def test_updates_enabled(self, tmp_dir):
        result = update_watcher_config(
            "github_review", enabled=False, config_dir=tmp_dir
        )
        watcher = result.get_watcher("github_review")

        assert watcher.enabled is False

    def test_updates_interval(self, tmp_dir):
        result = update_watcher_config(
            "github_review", interval_minutes=30, config_dir=tmp_dir
        )

        assert result.get_watcher("github_review").interval_minutes == 30

    def test_preserves_existing_config(self, tmp_dir):
        update_watcher_config("first", enabled=True, config_dir=tmp_dir)
        result = update_watcher_config("second", enabled=False, config_dir=tmp_dir)

        assert result.get_watcher("first").enabled is True
        assert result.get_watcher("second").enabled is False
