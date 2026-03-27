package terminal

import "io"

// Terminal abstracts a process execution environment.
type Terminal interface {
	Start(cfg TerminalConfig) error
	Stop() error
	IsRunning() bool

	Write(data []byte) (int, error)
	CaptureOutput() (string, error)
	HasChanged() bool

	Attach(stdin io.Reader, stdout io.Writer) (<-chan struct{}, error)
	Detach() error

	Resize(cols, rows uint16) error

	PID() (int, error)
	Name() string
}

// TerminalConfig holds parameters for starting a terminal.
type TerminalConfig struct {
	Name    string
	WorkDir string
	Command string
	Args    []string
	Env     []string
	Cols    uint16
	Rows    uint16
}
