package session

import "io"

// Manager defines the session management interface.
type Manager interface {
	// Lifecycle
	Create(cfg SessionConfig) (*Session, error)
	Start(sessionID string) error
	Pause(sessionID string) error
	Resume(sessionID string) error
	Kill(sessionID string) error

	// Query
	Get(sessionID string) (*Session, error)
	List() []*Session
	ListByStatus(status Status) []*Session

	// I/O
	SendInput(sessionID string, input []byte) error
	CaptureOutput(sessionID string) (string, error)
	HasOutputChanged(sessionID string) bool

	// Attach/Detach
	Attach(sessionID string, stdin io.Reader, stdout io.Writer) (<-chan struct{}, error)
	Detach(sessionID string) error

	// Metrics
	GetMetrics(sessionID string) (Metrics, error)
}
