package terminal

import (
	"fmt"
	"io"
	"os"
	"os/exec"
	"os/signal"
	"syscall"

	"github.com/creack/pty"
)

// Attach connects stdin/stdout to the tmux session via PTY.
// Returns a channel that closes when the session is detached.
func (t *TmuxTerminal) Attach(stdin io.Reader, stdout io.Writer) (<-chan struct{}, error) {
	t.mu.Lock()
	defer t.mu.Unlock()

	if t.attached {
		return nil, fmt.Errorf("already attached to %q", t.name)
	}

	if !t.IsRunning() {
		return nil, fmt.Errorf("tmux session %q is not running", t.name)
	}

	// Start PTY with tmux attach
	cmd := exec.Command("tmux", "attach-session", "-t", t.name)
	ptmx, err := pty.Start(cmd)
	if err != nil {
		return nil, fmt.Errorf("failed to attach PTY to %q: %w", t.name, err)
	}

	t.attached = true
	t.detachCh = make(chan struct{})
	t.ptyFile = ptmx
	doneCh := t.detachCh

	// Handle terminal resize (SIGWINCH)
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGWINCH)

	// Initial resize to match current terminal
	resizePTY(ptmx)

	// goroutine A: PTY → stdout (session output to user)
	go func() {
		defer func() {
			// Auto-detach when PTY closes (session exited)
			t.Detach()
		}()
		io.Copy(stdout, ptmx)
	}()

	// goroutine B: stdin → PTY (user input to session)
	go func() {
		buf := make([]byte, 1024)
		for {
			select {
			case <-doneCh:
				return
			default:
				n, err := stdin.Read(buf)
				if err != nil {
					return
				}
				if n > 0 {
					ptmx.Write(buf[:n])
				}
			}
		}
	}()

	// goroutine C: SIGWINCH → PTY resize
	go func() {
		defer signal.Stop(sigCh)
		for {
			select {
			case <-doneCh:
				return
			case <-sigCh:
				resizePTY(ptmx)
			}
		}
	}()

	return doneCh, nil
}

// Detach disconnects from the tmux session.
func (t *TmuxTerminal) Detach() error {
	t.mu.Lock()
	defer t.mu.Unlock()

	if !t.attached {
		return nil
	}

	t.attached = false
	if t.detachCh != nil {
		close(t.detachCh)
		t.detachCh = nil
	}
	if t.ptyFile != nil {
		t.ptyFile.Close()
		t.ptyFile = nil
	}

	return nil
}

// resizePTY sets the PTY size to match the current terminal dimensions.
func resizePTY(ptmx *os.File) {
	size, err := pty.GetsizeFull(os.Stdin)
	if err != nil {
		return
	}
	pty.Setsize(ptmx, size)
}
