package session

import (
	"fmt"
	"io"
	"sync"
	"time"

	"github.com/google/uuid"

	"github.com/agent-forge/agent-forge/runtime/internal/config"
	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/monitor"
	"github.com/agent-forge/agent-forge/runtime/internal/sandbox"
	"github.com/agent-forge/agent-forge/runtime/internal/terminal"
)

// SessionManager is the concrete implementation of Manager.
type SessionManager struct {
	sessions  map[string]*managedSession
	store     Store
	eventBus  event.Bus
	config    *config.Config
	mu        sync.RWMutex
	stopCh    chan struct{}
	monitor   *monitor.Monitor
}

// managedSession pairs a Session with its runtime resources.
type managedSession struct {
	Session  *Session
	Terminal terminal.Terminal
	Sandbox  *sandbox.Sandbox
}

// NewSessionManager creates a new SessionManager.
func NewSessionManager(cfg *config.Config, store Store, bus event.Bus) *SessionManager {
	return &SessionManager{
		sessions: make(map[string]*managedSession),
		store:    store,
		eventBus: bus,
		config:   cfg,
	}
}

// Create sets up a new session with sandbox and persists it.
func (m *SessionManager) Create(cfg SessionConfig) (*Session, error) {
	m.mu.Lock()
	defer m.mu.Unlock()

	// Resolve policy
	policyName := cfg.PolicyName
	if policyName == "" {
		policyName = m.config.DefaultPolicy
	}

	policy, ok := sandbox.Presets[policyName]
	if !ok {
		return nil, fmt.Errorf("unknown policy: %q", policyName)
	}

	if cfg.TokenBudget > 0 {
		policy.TokenBudget = cfg.TokenBudget
	}

	sessionID := uuid.New().String()
	now := time.Now()

	// Setup sandbox
	sbx, err := sandbox.Setup(sandbox.SandboxConfig{
		SessionID:   sessionID,
		Title:       cfg.Title,
		Policy:      policy,
		ProjectPath: cfg.ProjectPath,
		UseWorktree: cfg.UseWorktree,
		TaskPrompt:  cfg.Task,
		SessionsDir: m.config.Paths.SessionsDir,
	})
	if err != nil {
		return nil, fmt.Errorf("sandbox setup failed: %w", err)
	}

	sess := &Session{
		ID:          sessionID,
		Title:       cfg.Title,
		Task:        cfg.Task,
		Status:      StatusCreating,
		SandboxDir:  sbx.RootDir,
		PolicyName:  policyName,
		ProjectPath: cfg.ProjectPath,
		CreatedAt:   now,
		UpdatedAt:   now,
	}

	m.sessions[sessionID] = &managedSession{
		Session: sess,
		Sandbox: sbx,
	}

	if err := m.store.Save(sess); err != nil {
		return nil, fmt.Errorf("failed to persist session: %w", err)
	}

	m.publish(event.SessionCreated, sessionID, nil)

	return sess, nil
}

// Start launches Claude Code in a tmux terminal for the session.
func (m *SessionManager) Start(sessionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	if err := m.transition(ms.Session, StatusRunning); err != nil {
		return err
	}

	// Create and start terminal
	tmuxName := terminal.SessionName(sessionID)
	term := terminal.NewTmuxTerminal()

	termCfg := terminal.TerminalConfig{
		Name:    tmuxName,
		WorkDir: ms.Session.SandboxDir,
		Command: "claude",
		Cols:    200,
		Rows:    50,
	}

	if ms.Session.Task != "" {
		termCfg.Args = []string{fmt.Sprintf("%q", ms.Session.Task)}
	}

	if err := term.Start(termCfg); err != nil {
		m.transitionForce(ms.Session, StatusFailed, fmt.Sprintf("terminal start failed: %v", err))
		return fmt.Errorf("terminal start failed: %w", err)
	}

	ms.Terminal = term
	ms.Session.StartedAt = time.Now()
	ms.Session.UpdatedAt = time.Now()

	if err := m.store.Save(ms.Session); err != nil {
		return fmt.Errorf("failed to persist session: %w", err)
	}

	m.publish(event.SessionStarted, sessionID, nil)

	return nil
}

// Pause detaches the terminal and preserves the sandbox.
func (m *SessionManager) Pause(sessionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	if err := m.transition(ms.Session, StatusPaused); err != nil {
		return err
	}

	if ms.Terminal != nil {
		ms.Terminal.Detach()
	}

	if ms.Sandbox != nil {
		if err := ms.Sandbox.Preserve(); err != nil {
			return fmt.Errorf("sandbox preserve failed: %w", err)
		}
	}

	ms.Session.UpdatedAt = time.Now()
	if err := m.store.Save(ms.Session); err != nil {
		return fmt.Errorf("failed to persist session: %w", err)
	}

	m.publish(event.SessionStatusChanged, sessionID, StatusPaused)

	return nil
}

// Resume reconnects to a paused session's tmux.
func (m *SessionManager) Resume(sessionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	if err := m.transition(ms.Session, StatusRunning); err != nil {
		return err
	}

	// Reconnect terminal if needed
	if ms.Terminal == nil || !ms.Terminal.IsRunning() {
		tmuxName := terminal.SessionName(sessionID)
		term, ok := terminal.Reconnect(tmuxName)
		if !ok {
			m.transitionForce(ms.Session, StatusFailed, "tmux session no longer exists")
			return fmt.Errorf("tmux session %q no longer exists", tmuxName)
		}
		ms.Terminal = term
	}

	ms.Session.UpdatedAt = time.Now()
	if err := m.store.Save(ms.Session); err != nil {
		return fmt.Errorf("failed to persist session: %w", err)
	}

	m.publish(event.SessionStatusChanged, sessionID, StatusRunning)

	return nil
}

// Kill terminates the session, stops the terminal, and cleans up.
func (m *SessionManager) Kill(sessionID string) error {
	m.mu.Lock()
	defer m.mu.Unlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	// Stop terminal
	if ms.Terminal != nil {
		ms.Terminal.Stop()
	}

	// Teardown sandbox
	if ms.Sandbox != nil {
		ms.Sandbox.Teardown()
	}

	ms.Session.Status = StatusCompleted
	ms.Session.CompletedAt = time.Now()
	ms.Session.UpdatedAt = time.Now()

	if err := m.store.Save(ms.Session); err != nil {
		return fmt.Errorf("failed to persist session: %w", err)
	}

	m.publish(event.SessionCompleted, sessionID, nil)

	return nil
}

// Get returns a session by ID.
func (m *SessionManager) Get(sessionID string) (*Session, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return nil, err
	}

	return ms.Session, nil
}

// List returns all sessions.
func (m *SessionManager) List() []*Session {
	m.mu.RLock()
	defer m.mu.RUnlock()

	result := make([]*Session, 0, len(m.sessions))
	for _, ms := range m.sessions {
		result = append(result, ms.Session)
	}
	return result
}

// ListByStatus returns sessions matching the given status.
func (m *SessionManager) ListByStatus(status Status) []*Session {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var result []*Session
	for _, ms := range m.sessions {
		if ms.Session.Status == status {
			result = append(result, ms.Session)
		}
	}
	return result
}

// SendInput sends data to the session's terminal.
func (m *SessionManager) SendInput(sessionID string, input []byte) error {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	if ms.Terminal == nil {
		return fmt.Errorf("session %q has no terminal", sessionID)
	}

	_, err = ms.Terminal.Write(input)
	return err
}

// CaptureOutput captures the terminal output for a session.
func (m *SessionManager) CaptureOutput(sessionID string) (string, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return "", err
	}

	if ms.Terminal == nil {
		return "", fmt.Errorf("session %q has no terminal", sessionID)
	}

	return ms.Terminal.CaptureOutput()
}

// HasOutputChanged checks if the terminal output has changed.
func (m *SessionManager) HasOutputChanged(sessionID string) bool {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return false
	}

	if ms.Terminal == nil {
		return false
	}

	return ms.Terminal.HasChanged()
}

// Attach connects stdin/stdout to the session's terminal.
func (m *SessionManager) Attach(sessionID string, stdin io.Reader, stdout io.Writer) (<-chan struct{}, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return nil, err
	}

	if ms.Terminal == nil {
		return nil, fmt.Errorf("session %q has no terminal", sessionID)
	}

	return ms.Terminal.Attach(stdin, stdout)
}

// Detach disconnects from the session's terminal.
func (m *SessionManager) Detach(sessionID string) error {
	m.mu.RLock()
	defer m.mu.RUnlock()

	ms, err := m.getManagedSession(sessionID)
	if err != nil {
		return err
	}

	if ms.Terminal == nil {
		return nil
	}

	return ms.Terminal.Detach()
}

// GetMetrics returns the latest metrics for a session.
func (m *SessionManager) GetMetrics(sessionID string) (Metrics, error) {
	m.mu.RLock()
	defer m.mu.RUnlock()

	if _, err := m.getManagedSession(sessionID); err != nil {
		return Metrics{}, err
	}

	// Placeholder — M5 will integrate real metrics collection
	return Metrics{
		CollectedAt: time.Now(),
	}, nil
}

// Restore loads sessions from store and reconciles with tmux state.
func (m *SessionManager) Restore() error {
	m.mu.Lock()
	defer m.mu.Unlock()

	sessions, err := m.store.LoadAll()
	if err != nil {
		return fmt.Errorf("failed to load sessions: %w", err)
	}

	for _, sess := range sessions {
		ms := &managedSession{Session: sess}

		switch sess.Status {
		case StatusRunning, StatusWaiting:
			// Try to reconnect to existing tmux session
			tmuxName := terminal.SessionName(sess.ID)
			if term, ok := terminal.Reconnect(tmuxName); ok {
				ms.Terminal = term
			} else {
				// tmux session gone → mark as failed
				sess.Status = StatusFailed
				sess.ErrorMsg = "tmux session lost after process restart"
				sess.UpdatedAt = time.Now()
				m.store.Save(sess)
			}

		case StatusCreating:
			// Check if sandbox was fully created
			if sess.SandboxDir == "" {
				sess.Status = StatusFailed
				sess.ErrorMsg = "interrupted during creation"
				sess.UpdatedAt = time.Now()
				m.store.Save(sess)
			}
			// Otherwise keep as creating — waiting for Start

		case StatusPaused, StatusCompleted, StatusFailed:
			// Keep as-is
		}

		m.sessions[sess.ID] = ms
	}

	return nil
}

// transition validates and applies a state change.
func (m *SessionManager) transition(sess *Session, to Status) error {
	t := ValidateTransition(sess.Status, to)
	if t == nil {
		return fmt.Errorf("invalid transition: %s → %s", sess.Status, to)
	}

	if t.Guard != nil {
		if err := t.Guard(sess); err != nil {
			return fmt.Errorf("transition guard failed (%s → %s): %w", sess.Status, to, err)
		}
	}

	sess.Status = to
	return nil
}

// transitionForce forces a status change (for error paths).
func (m *SessionManager) transitionForce(sess *Session, to Status, errMsg string) {
	sess.Status = to
	sess.ErrorMsg = errMsg
	sess.UpdatedAt = time.Now()
	m.store.Save(sess)
}

func (m *SessionManager) getManagedSession(id string) (*managedSession, error) {
	ms, ok := m.sessions[id]
	if !ok {
		return nil, fmt.Errorf("session not found: %s", id)
	}
	return ms, nil
}

func (m *SessionManager) publish(eventType event.Type, sessionID string, data any) {
	if m.eventBus == nil {
		return
	}
	m.eventBus.Publish(event.Event{
		Type:      eventType,
		SessionID: sessionID,
		Data:      data,
		Timestamp: time.Now(),
	})
}
