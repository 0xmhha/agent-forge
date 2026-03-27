package daemon

import (
	"fmt"
	"os"
	"os/exec"
	"strconv"
	"strings"
	"syscall"
)

// Daemon manages the background forge process.
type Daemon struct {
	PIDFile    string
	LogFile    string
	BinaryPath string
}

// NewDaemon creates a new Daemon instance.
func NewDaemon(pidFile, logFile string) *Daemon {
	bin, _ := os.Executable()
	return &Daemon{
		PIDFile:    pidFile,
		LogFile:    logFile,
		BinaryPath: bin,
	}
}

// Start launches the daemon as a background process.
func (d *Daemon) Start() error {
	if pid, running := d.Status(); running {
		return fmt.Errorf("daemon already running (PID %d)", pid)
	}

	logFile, err := os.OpenFile(d.LogFile, os.O_CREATE|os.O_WRONLY|os.O_APPEND, 0640)
	if err != nil {
		return fmt.Errorf("failed to open log file: %w", err)
	}

	cmd := exec.Command(d.BinaryPath, "daemon", "run")
	cmd.Stdout = logFile
	cmd.Stderr = logFile
	cmd.SysProcAttr = &syscall.SysProcAttr{
		Setsid: true, // Detach from terminal
	}

	if err := cmd.Start(); err != nil {
		logFile.Close()
		return fmt.Errorf("failed to start daemon: %w", err)
	}

	logFile.Close()

	if err := d.writePID(cmd.Process.Pid); err != nil {
		return fmt.Errorf("failed to write PID file: %w", err)
	}

	return nil
}

// Stop kills the running daemon.
func (d *Daemon) Stop() error {
	pid, running := d.Status()
	if !running {
		return fmt.Errorf("daemon is not running")
	}

	process, err := os.FindProcess(pid)
	if err != nil {
		return fmt.Errorf("failed to find process %d: %w", pid, err)
	}

	if err := process.Signal(syscall.SIGTERM); err != nil {
		return fmt.Errorf("failed to stop daemon (PID %d): %w", pid, err)
	}

	os.Remove(d.PIDFile)
	return nil
}

// Status returns the PID and whether the daemon is running.
func (d *Daemon) Status() (int, bool) {
	pid, err := d.readPID()
	if err != nil {
		return 0, false
	}

	process, err := os.FindProcess(pid)
	if err != nil {
		return pid, false
	}

	// Check if process is alive by sending signal 0
	if err := process.Signal(syscall.Signal(0)); err != nil {
		os.Remove(d.PIDFile)
		return pid, false
	}

	return pid, true
}

func (d *Daemon) writePID(pid int) error {
	return os.WriteFile(d.PIDFile, []byte(strconv.Itoa(pid)), 0640)
}

func (d *Daemon) readPID() (int, error) {
	data, err := os.ReadFile(d.PIDFile)
	if err != nil {
		return 0, err
	}

	pid, err := strconv.Atoi(strings.TrimSpace(string(data)))
	if err != nil {
		return 0, fmt.Errorf("invalid PID file content: %w", err)
	}

	return pid, nil
}
