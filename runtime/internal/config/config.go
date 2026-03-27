package config

import (
	"encoding/json"
	"errors"
	"os"
)

// Config holds application-level configuration.
type Config struct {
	DefaultPolicy string `json:"default_policy"`
	LogLevel      string `json:"log_level"`
	DaemonEnabled bool   `json:"daemon_enabled"`

	// Monitor intervals (seconds)
	CaptureIntervalMs int `json:"capture_interval_ms"`
	MetricsIntervalMs int `json:"metrics_interval_ms"`

	Paths Paths `json:"-"`
}

// DefaultConfig returns a Config with sensible defaults.
func DefaultConfig() Config {
	return Config{
		DefaultPolicy:     "standard",
		LogLevel:          "info",
		DaemonEnabled:     false,
		CaptureIntervalMs: 200,
		MetricsIntervalMs: 2000,
	}
}

// Load reads configuration from the config file.
// Returns default config if the file does not exist.
func Load() (*Config, error) {
	paths, err := ResolvePaths()
	if err != nil {
		return nil, err
	}

	cfg := DefaultConfig()
	cfg.Paths = paths

	data, err := os.ReadFile(paths.Config)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return &cfg, nil
		}
		return nil, err
	}

	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, err
	}

	cfg.Paths = paths
	return &cfg, nil
}

// Save writes the current configuration to disk.
func (c *Config) Save() error {
	if err := c.Paths.EnsureDirs(); err != nil {
		return err
	}

	data, err := json.MarshalIndent(c, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(c.Paths.Config, data, 0640)
}
