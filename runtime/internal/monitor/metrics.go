package monitor

import "time"

// Snapshot holds a complete metrics snapshot for a session.
type Snapshot struct {
	SessionID     string    `json:"session_id"`
	CPUPercent    float64   `json:"cpu_percent"`
	MemoryMB      float64   `json:"memory_mb"`
	TokensUsed    int64     `json:"tokens_used"`
	TokenBudget   int64     `json:"token_budget"`
	NetworkActive bool      `json:"network_active"`
	CollectedAt   time.Time `json:"collected_at"`
}

// Collector gathers a specific kind of metric.
type Collector interface {
	Name() string
	Collect(pid int, output string) (CollectorResult, error)
}

// CollectorResult holds the output from a single collector.
type CollectorResult struct {
	CPUPercent    float64
	MemoryMB      float64
	TokensUsed    int64
	NetworkActive bool
}
