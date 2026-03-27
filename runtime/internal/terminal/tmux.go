package terminal

import (
	"fmt"
	"io"
	"os/exec"
	"strconv"
	"strings"
	"sync"
)

// TmuxTerminal implements Terminal using tmux sessions.
type TmuxTerminal struct {
	name    string
	tracker OutputTracker

	// Attach state
	mu       sync.Mutex
	attached bool
	detachCh chan struct{}
	ptyFile  io.Closer
}

// NewTmuxTerminal creates a new TmuxTerminal instance.
func NewTmuxTerminal() *TmuxTerminal {
	return &TmuxTerminal{}
}

// Start creates a new tmux session and runs the specified command.
func (t *TmuxTerminal) Start(cfg TerminalConfig) error {
	t.name = cfg.Name

	args := []string{
		"new-session",
		"-d",
		"-s", t.name,
		"-x", strconv.Itoa(int(cfg.Cols)),
		"-y", strconv.Itoa(int(cfg.Rows)),
	}

	if cfg.WorkDir != "" {
		args = append(args, "-c", cfg.WorkDir)
	}

	// Build the shell command for tmux to execute.
	// tmux new-session takes a single shell-command string as its last argument.
	// We must combine Command + Args into one properly quoted string.
	if cfg.Command != "" {
		parts := []string{cfg.Command}
		parts = append(parts, cfg.Args...)
		args = append(args, strings.Join(parts, " "))
	}

	cmd := exec.Command("tmux", args...)

	// Set environment variables
	if len(cfg.Env) > 0 {
		cmd.Env = append(cmd.Environ(), cfg.Env...)
	}

	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to start tmux session %q: %w\n%s", t.name, err, string(output))
	}

	return nil
}

// Stop kills the tmux session.
func (t *TmuxTerminal) Stop() error {
	t.Detach()

	cmd := exec.Command("tmux", "kill-session", "-t", t.name)
	if output, err := cmd.CombinedOutput(); err != nil {
		// Session might already be dead
		if strings.Contains(string(output), "can't find session") {
			return nil
		}
		return fmt.Errorf("failed to kill tmux session %q: %w", t.name, err)
	}

	return nil
}

// IsRunning checks if the tmux session exists.
func (t *TmuxTerminal) IsRunning() bool {
	cmd := exec.Command("tmux", "has-session", "-t", t.name)
	return cmd.Run() == nil
}

// Write sends input to the tmux session via send-keys.
func (t *TmuxTerminal) Write(data []byte) (int, error) {
	// Use send-keys with literal flag to send exact bytes
	cmd := exec.Command("tmux", "send-keys", "-t", t.name, "-l", string(data))
	if output, err := cmd.CombinedOutput(); err != nil {
		return 0, fmt.Errorf("failed to send keys to %q: %w\n%s", t.name, err, string(output))
	}

	return len(data), nil
}

// CaptureOutput captures the current pane content.
func (t *TmuxTerminal) CaptureOutput() (string, error) {
	cmd := exec.Command("tmux", "capture-pane", "-t", t.name, "-p", "-S", "-")
	output, err := cmd.Output()
	if err != nil {
		return "", fmt.Errorf("failed to capture output from %q: %w", t.name, err)
	}

	return strings.TrimRight(string(output), "\n"), nil
}

// HasChanged returns true if the terminal output has changed since last check.
func (t *TmuxTerminal) HasChanged() bool {
	output, err := t.CaptureOutput()
	if err != nil {
		return false
	}
	return t.tracker.HasChanged(output)
}

// Resize changes the tmux window dimensions.
func (t *TmuxTerminal) Resize(cols, rows uint16) error {
	cmd := exec.Command("tmux", "resize-window", "-t", t.name,
		"-x", strconv.Itoa(int(cols)),
		"-y", strconv.Itoa(int(rows)),
	)
	if output, err := cmd.CombinedOutput(); err != nil {
		return fmt.Errorf("failed to resize %q: %w\n%s", t.name, err, string(output))
	}
	return nil
}

// PID returns the process ID of the command running in the tmux pane.
func (t *TmuxTerminal) PID() (int, error) {
	cmd := exec.Command("tmux", "list-panes", "-t", t.name, "-F", "#{pane_pid}")
	output, err := cmd.Output()
	if err != nil {
		return 0, fmt.Errorf("failed to get PID for %q: %w", t.name, err)
	}

	pidStr := strings.TrimSpace(string(output))
	pid, err := strconv.Atoi(pidStr)
	if err != nil {
		return 0, fmt.Errorf("invalid PID %q: %w", pidStr, err)
	}

	return pid, nil
}

// Name returns the tmux session name.
func (t *TmuxTerminal) Name() string {
	return t.name
}

// Reconnect attaches to an existing tmux session by name (no new session created).
// Returns false if the session does not exist.
func Reconnect(name string) (*TmuxTerminal, bool) {
	t := &TmuxTerminal{name: name}
	if !t.IsRunning() {
		return nil, false
	}
	return t, true
}

// SessionName generates a tmux session name from a session ID.
// Format: forge_{first 8 chars of ID}
func SessionName(sessionID string) string {
	id := sessionID
	if len(id) > 8 {
		id = id[:8]
	}
	return "forge_" + id
}

