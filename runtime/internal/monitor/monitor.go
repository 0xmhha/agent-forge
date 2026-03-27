package monitor

import (
	"sync"
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/event"
)

// SessionTarget provides the information Monitor needs from sessions.
// This avoids a direct dependency on the session package.
type SessionTarget struct {
	SessionID string
	PID       int
	Output    string
}

// TargetProvider returns currently active sessions to monitor.
type TargetProvider func() []SessionTarget

// Monitor periodically collects metrics for active sessions.
type Monitor struct {
	interval   time.Duration
	collectors []Collector
	eventBus   event.Bus
	provider   TargetProvider

	mu        sync.Mutex
	snapshots map[string]Snapshot // sessionID → latest snapshot
	stopCh    chan struct{}
	running   bool
}

// NewMonitor creates a new Monitor.
func NewMonitor(interval time.Duration, bus event.Bus, provider TargetProvider) *Monitor {
	return &Monitor{
		interval: interval,
		collectors: []Collector{
			&ProcessCollector{},
			&TokenCollector{},
		},
		eventBus:  bus,
		provider:  provider,
		snapshots: make(map[string]Snapshot),
	}
}

// Start begins periodic metric collection in a goroutine.
func (m *Monitor) Start() {
	m.mu.Lock()
	if m.running {
		m.mu.Unlock()
		return
	}
	m.stopCh = make(chan struct{})
	m.running = true
	m.mu.Unlock()

	go m.loop()
}

// Stop halts metric collection.
func (m *Monitor) Stop() {
	m.mu.Lock()
	defer m.mu.Unlock()

	if !m.running {
		return
	}

	close(m.stopCh)
	m.running = false
}

// GetSnapshot returns the latest metrics for a session.
func (m *Monitor) GetSnapshot(sessionID string) (Snapshot, bool) {
	m.mu.Lock()
	defer m.mu.Unlock()

	snap, ok := m.snapshots[sessionID]
	return snap, ok
}

func (m *Monitor) loop() {
	ticker := time.NewTicker(m.interval)
	defer ticker.Stop()

	for {
		select {
		case <-m.stopCh:
			return
		case <-ticker.C:
			m.collect()
		}
	}
}

func (m *Monitor) collect() {
	targets := m.provider()

	for _, target := range targets {
		snap := Snapshot{
			SessionID:   target.SessionID,
			CollectedAt: time.Now(),
		}

		for _, collector := range m.collectors {
			result, err := collector.Collect(target.PID, target.Output)
			if err != nil {
				continue
			}
			mergeResult(&snap, result)
		}

		m.mu.Lock()
		m.snapshots[target.SessionID] = snap
		m.mu.Unlock()

		if m.eventBus != nil {
			m.eventBus.Publish(event.Event{
				Type:      event.MetricsUpdated,
				SessionID: target.SessionID,
				Data:      snap,
				Timestamp: snap.CollectedAt,
			})
		}
	}
}

func mergeResult(snap *Snapshot, result CollectorResult) {
	if result.CPUPercent > 0 {
		snap.CPUPercent = result.CPUPercent
	}
	if result.MemoryMB > 0 {
		snap.MemoryMB = result.MemoryMB
	}
	if result.TokensUsed > 0 {
		snap.TokensUsed = result.TokensUsed
	}
	if result.NetworkActive {
		snap.NetworkActive = true
	}
}
