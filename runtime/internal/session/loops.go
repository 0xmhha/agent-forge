package session

import (
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/monitor"
)

// StartLoops begins background capture and status monitoring loops.
func (m *SessionManager) StartLoops() {
	m.mu.Lock()
	if m.stopCh != nil {
		m.mu.Unlock()
		return
	}
	m.stopCh = make(chan struct{})
	m.mu.Unlock()

	go m.captureLoop()
	go m.statusLoop()

	// Start metrics monitor
	mon := monitor.NewMonitor(
		time.Duration(m.config.MetricsIntervalMs)*time.Millisecond,
		m.eventBus,
		m.monitorTargets,
	)
	m.mu.Lock()
	m.monitor = mon
	m.mu.Unlock()
	mon.Start()
}

// StopLoops stops all background loops.
func (m *SessionManager) StopLoops() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if m.stopCh != nil {
		close(m.stopCh)
		m.stopCh = nil
	}
	if m.monitor != nil {
		m.monitor.Stop()
		m.monitor = nil
	}
}

// captureLoop periodically captures output from active sessions.
func (m *SessionManager) captureLoop() {
	interval := time.Duration(m.config.CaptureIntervalMs) * time.Millisecond
	ticker := time.NewTicker(interval)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopCh:
			return
		case <-ticker.C:
			m.checkOutputChanges()
		}
	}
}

// statusLoop periodically checks if running sessions are still alive.
func (m *SessionManager) statusLoop() {
	ticker := time.NewTicker(time.Second)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopCh:
			return
		case <-ticker.C:
			m.checkSessionStatuses()
		}
	}
}

func (m *SessionManager) checkOutputChanges() {
	m.mu.RLock()
	var active []struct {
		id string
		ms *managedSession
	}
	for id, ms := range m.sessions {
		if ms.Terminal != nil && (ms.Session.Status == StatusRunning || ms.Session.Status == StatusWaiting) {
			active = append(active, struct {
				id string
				ms *managedSession
			}{id, ms})
		}
	}
	m.mu.RUnlock()

	for _, a := range active {
		if a.ms.Terminal.HasChanged() {
			m.publish(event.SessionOutputChanged, a.id, nil)
		}
	}
}

func (m *SessionManager) checkSessionStatuses() {
	m.mu.Lock()
	defer m.mu.Unlock()

	for _, ms := range m.sessions {
		if ms.Session.Status != StatusRunning && ms.Session.Status != StatusWaiting {
			continue
		}

		if ms.Terminal == nil || !ms.Terminal.IsRunning() {
			// Process has exited
			ms.Session.Status = StatusCompleted
			ms.Session.CompletedAt = time.Now()
			ms.Session.UpdatedAt = time.Now()
			m.store.Save(ms.Session)
			m.publish(event.SessionCompleted, ms.Session.ID, nil)
		}
	}
}

// monitorTargets provides active session info to the Monitor.
func (m *SessionManager) monitorTargets() []monitor.SessionTarget {
	m.mu.RLock()
	defer m.mu.RUnlock()

	var targets []monitor.SessionTarget
	for _, ms := range m.sessions {
		if ms.Terminal == nil || ms.Session.Status != StatusRunning {
			continue
		}

		pid, err := ms.Terminal.PID()
		if err != nil {
			continue
		}

		output, _ := ms.Terminal.CaptureOutput()

		targets = append(targets, monitor.SessionTarget{
			SessionID: ms.Session.ID,
			PID:       pid,
			Output:    output,
		})
	}

	return targets
}

// GetMetricsSnapshot returns the latest monitor snapshot for a session.
func (m *SessionManager) GetMetricsSnapshot(sessionID string) (monitor.Snapshot, bool) {
	m.mu.RLock()
	mon := m.monitor
	m.mu.RUnlock()

	if mon == nil {
		return monitor.Snapshot{}, false
	}
	return mon.GetSnapshot(sessionID)
}
