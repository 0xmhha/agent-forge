package session

import (
	"encoding/json"
	"fmt"
	"time"
)

// Status represents the lifecycle state of a session.
type Status int

const (
	StatusCreating  Status = iota // Sandbox being configured
	StatusRunning                 // Claude Code executing
	StatusWaiting                 // Awaiting user input
	StatusPaused                  // Detached, sandbox preserved
	StatusCompleted               // Task finished successfully
	StatusFailed                  // Error occurred
)

func (s Status) String() string {
	switch s {
	case StatusCreating:
		return "creating"
	case StatusRunning:
		return "running"
	case StatusWaiting:
		return "waiting"
	case StatusPaused:
		return "paused"
	case StatusCompleted:
		return "completed"
	case StatusFailed:
		return "failed"
	default:
		return "unknown"
	}
}

// MarshalJSON encodes Status as a string for readability.
func (s Status) MarshalJSON() ([]byte, error) {
	return json.Marshal(s.String())
}

// UnmarshalJSON decodes Status from a string.
func (s *Status) UnmarshalJSON(data []byte) error {
	var str string
	if err := json.Unmarshal(data, &str); err != nil {
		return err
	}

	switch str {
	case "creating":
		*s = StatusCreating
	case "running":
		*s = StatusRunning
	case "waiting":
		*s = StatusWaiting
	case "paused":
		*s = StatusPaused
	case "completed":
		*s = StatusCompleted
	case "failed":
		*s = StatusFailed
	default:
		return fmt.Errorf("unknown status: %q", str)
	}
	return nil
}

// SessionConfig holds parameters for creating a new session.
type SessionConfig struct {
	Title       string
	Task        string
	ProjectPath string
	PolicyName  string
	UseWorktree bool
	TokenBudget int64
}

// Session represents a managed Claude Code execution environment.
type Session struct {
	ID          string    `json:"id"`
	Title       string    `json:"title"`
	Task        string    `json:"task"`
	Status      Status    `json:"status"`
	ExitCode    int       `json:"exit_code"`
	ErrorMsg    string    `json:"error_msg,omitempty"`
	SandboxDir  string    `json:"sandbox_dir"`
	PolicyName  string    `json:"policy_name"`
	ProjectPath string    `json:"project_path,omitempty"`
	CreatedAt   time.Time `json:"created_at"`
	StartedAt   time.Time `json:"started_at,omitempty"`
	UpdatedAt   time.Time `json:"updated_at"`
	CompletedAt time.Time `json:"completed_at,omitempty"`
}

// Metrics holds resource usage snapshot for a session.
type Metrics struct {
	CPUPercent    float64   `json:"cpu_percent"`
	MemoryMB      float64   `json:"memory_mb"`
	TokensUsed    int64     `json:"tokens_used"`
	TokenBudget   int64     `json:"token_budget"`
	NetworkActive bool      `json:"network_active"`
	CollectedAt   time.Time `json:"collected_at"`
}
