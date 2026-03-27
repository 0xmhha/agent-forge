package terminal_test

import (
	"os/exec"
	"testing"
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/terminal"
)

func TestTmuxTerminalIntegration(t *testing.T) {
	// Skip if tmux is not available
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux not found, skipping integration test")
	}

	term := terminal.NewTmuxTerminal()
	sessionName := "forge_inttest"

	// Cleanup in case previous test left a session
	exec.Command("tmux", "kill-session", "-t", sessionName).Run()

	// 1. Start
	// tmux new-session takes a single shell-command string.
	// We pass the whole command as Command, since tmux runs it via sh -c.
	cfg := terminal.TerminalConfig{
		Name:    sessionName,
		WorkDir: "/tmp",
		Command: "bash -c 'echo Hello_from_forge; sleep 30'",
		Cols:    80,
		Rows:    24,
	}

	if err := term.Start(cfg); err != nil {
		t.Fatalf("Start failed: %v", err)
	}
	defer term.Stop()

	// 2. IsRunning
	if !term.IsRunning() {
		t.Fatal("expected IsRunning to be true after Start")
	}

	// 3. Wait for output with retry
	var output string
	var err error
	for i := 0; i < 10; i++ {
		time.Sleep(200 * time.Millisecond)
		output, err = term.CaptureOutput()
		if err != nil {
			t.Fatalf("CaptureOutput failed: %v", err)
		}
		if output != "" {
			break
		}
	}
	if output == "" {
		t.Fatal("expected non-empty output from CaptureOutput after retries")
	}
	t.Logf("Captured output (first 200 chars): %q", truncateStr(output, 200))

	// 5. HasChanged
	changed := term.HasChanged()
	if !changed {
		t.Error("expected HasChanged to be true on first call")
	}

	changed2 := term.HasChanged()
	if changed2 {
		t.Error("expected HasChanged to be false on second call without changes")
	}

	// 6. PID
	pid, err := term.PID()
	if err != nil {
		t.Fatalf("PID failed: %v", err)
	}
	if pid <= 0 {
		t.Errorf("expected valid PID, got %d", pid)
	}
	t.Logf("PID: %d", pid)

	// 7. Name
	if term.Name() != sessionName {
		t.Errorf("expected name %q, got %q", sessionName, term.Name())
	}

	// 8. Stop
	if err := term.Stop(); err != nil {
		t.Fatalf("Stop failed: %v", err)
	}

	// 9. IsRunning after stop
	if term.IsRunning() {
		t.Error("expected IsRunning to be false after Stop")
	}
}

func truncateStr(s string, n int) string {
	if len(s) > n {
		return s[:n]
	}
	return s
}
