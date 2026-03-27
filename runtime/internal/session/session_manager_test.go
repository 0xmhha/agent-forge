package session_test

import (
	"os"
	"os/exec"
	"testing"
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/config"
	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

func TestSessionManagerLifecycle(t *testing.T) {
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux not found, skipping integration test")
	}

	// Setup temp directory
	tmpDir, err := os.MkdirTemp("", "forge-test-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	cfg := &config.Config{
		DefaultPolicy: "standard",
		Paths: config.Paths{
			Root:        tmpDir,
			State:       tmpDir + "/state.json",
			SessionsDir: tmpDir + "/sessions",
		},
	}
	cfg.Paths.EnsureDirs()

	store := session.NewFileStore(cfg.Paths.State)
	bus := event.NewChannelBus(64)
	defer bus.Close()

	mgr := session.NewSessionManager(cfg, store, bus)

	// Subscribe to events
	eventCh := bus.Subscribe(
		event.SessionCreated,
		event.SessionStarted,
		event.SessionStatusChanged,
		event.SessionCompleted,
	)

	// === 1. Create ===
	t.Run("Create", func(t *testing.T) {
		sess, err := mgr.Create(session.SessionConfig{
			Title: "lifecycle-test",
			Task:  "echo test",
		})
		if err != nil {
			t.Fatalf("Create failed: %v", err)
		}

		if sess.Status != session.StatusCreating {
			t.Errorf("expected status creating, got %s", sess.Status)
		}

		if sess.SandboxDir == "" {
			t.Error("expected non-empty sandbox dir")
		}

		// Check event
		select {
		case evt := <-eventCh:
			if evt.Type != event.SessionCreated {
				t.Errorf("expected SessionCreated event, got %s", evt.Type)
			}
		case <-time.After(time.Second):
			t.Error("timeout waiting for SessionCreated event")
		}

		t.Logf("Created session: %s", sess.ID[:8])
	})

	// === 2. Start ===
	sessions := mgr.List()
	if len(sessions) == 0 {
		t.Fatal("no sessions found after Create")
	}
	sess := sessions[0]

	t.Run("Start", func(t *testing.T) {
		if err := mgr.Start(sess.ID); err != nil {
			t.Fatalf("Start failed: %v", err)
		}

		updated, _ := mgr.Get(sess.ID)
		if updated.Status != session.StatusRunning {
			t.Errorf("expected status running, got %s", updated.Status)
		}

		select {
		case evt := <-eventCh:
			if evt.Type != event.SessionStarted {
				t.Errorf("expected SessionStarted event, got %s", evt.Type)
			}
		case <-time.After(time.Second):
			t.Error("timeout waiting for SessionStarted event")
		}
	})

	// === 3. Pause ===
	t.Run("Pause", func(t *testing.T) {
		if err := mgr.Pause(sess.ID); err != nil {
			t.Fatalf("Pause failed: %v", err)
		}

		updated, _ := mgr.Get(sess.ID)
		if updated.Status != session.StatusPaused {
			t.Errorf("expected status paused, got %s", updated.Status)
		}

		select {
		case evt := <-eventCh:
			if evt.Type != event.SessionStatusChanged {
				t.Errorf("expected SessionStatusChanged event, got %s", evt.Type)
			}
		case <-time.After(time.Second):
			t.Error("timeout waiting for StatusChanged event")
		}
	})

	// === 4. Resume ===
	t.Run("Resume", func(t *testing.T) {
		if err := mgr.Resume(sess.ID); err != nil {
			t.Fatalf("Resume failed: %v", err)
		}

		updated, _ := mgr.Get(sess.ID)
		if updated.Status != session.StatusRunning {
			t.Errorf("expected status running, got %s", updated.Status)
		}

		select {
		case evt := <-eventCh:
			if evt.Type != event.SessionStatusChanged {
				t.Errorf("expected SessionStatusChanged event, got %s", evt.Type)
			}
		case <-time.After(time.Second):
			t.Error("timeout waiting for StatusChanged event")
		}
	})

	// === 5. Kill ===
	t.Run("Kill", func(t *testing.T) {
		if err := mgr.Kill(sess.ID); err != nil {
			t.Fatalf("Kill failed: %v", err)
		}

		updated, _ := mgr.Get(sess.ID)
		if updated.Status != session.StatusCompleted {
			t.Errorf("expected status completed, got %s", updated.Status)
		}

		select {
		case evt := <-eventCh:
			if evt.Type != event.SessionCompleted {
				t.Errorf("expected SessionCompleted event, got %s", evt.Type)
			}
		case <-time.After(time.Second):
			t.Error("timeout waiting for SessionCompleted event")
		}
	})

	// === 6. List by status ===
	t.Run("ListByStatus", func(t *testing.T) {
		completed := mgr.ListByStatus(session.StatusCompleted)
		if len(completed) != 1 {
			t.Errorf("expected 1 completed session, got %d", len(completed))
		}

		running := mgr.ListByStatus(session.StatusRunning)
		if len(running) != 0 {
			t.Errorf("expected 0 running sessions, got %d", len(running))
		}
	})
}

func TestSessionManagerRestore(t *testing.T) {
	if _, err := exec.LookPath("tmux"); err != nil {
		t.Skip("tmux not found, skipping integration test")
	}

	tmpDir, err := os.MkdirTemp("", "forge-restore-*")
	if err != nil {
		t.Fatal(err)
	}
	defer os.RemoveAll(tmpDir)

	cfg := &config.Config{
		DefaultPolicy: "standard",
		Paths: config.Paths{
			Root:        tmpDir,
			State:       tmpDir + "/state.json",
			SessionsDir: tmpDir + "/sessions",
		},
	}
	cfg.Paths.EnsureDirs()

	store := session.NewFileStore(cfg.Paths.State)
	bus := event.NewChannelBus(64)
	defer bus.Close()

	// Create and start a session, then "simulate restart" by creating a new manager
	mgr1 := session.NewSessionManager(cfg, store, bus)
	sess, err := mgr1.Create(session.SessionConfig{
		Title: "restore-test",
		Task:  "sleep 60",
	})
	if err != nil {
		t.Fatal(err)
	}

	if err := mgr1.Start(sess.ID); err != nil {
		t.Fatal(err)
	}

	// Simulate process restart — new manager, same store
	mgr2 := session.NewSessionManager(cfg, store, bus)
	if err := mgr2.Restore(); err != nil {
		t.Fatalf("Restore failed: %v", err)
	}

	restored, err := mgr2.Get(sess.ID)
	if err != nil {
		t.Fatalf("Get after restore failed: %v", err)
	}

	// Session should still be running (tmux session exists)
	if restored.Status != session.StatusRunning {
		t.Errorf("expected restored status running, got %s", restored.Status)
	}

	// Cleanup
	mgr2.Kill(sess.ID)
}
