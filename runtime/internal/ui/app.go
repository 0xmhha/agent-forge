package ui

import (
	"fmt"
	"strings"
	"time"

	"github.com/charmbracelet/bubbles/key"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"

	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/monitor"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
	"github.com/agent-forge/agent-forge/runtime/internal/ui/overlay"
)

// Mode represents the current UI mode.
type Mode int

const (
	ModeNormal Mode = iota
	ModeNewSession
	ModeConfirmKill
	ModeHelp
)

// Model is the BubbleTea application model.
type Model struct {
	// Dependencies
	Manager  *session.SessionManager
	EventBus event.Bus
	EventCh  <-chan event.Event

	// State
	Keys     KeyMap
	Mode     Mode
	Layout   Layout
	Sessions []*session.Session
	Selected int
	Preview  string
	Snapshot monitor.Snapshot
	FocusIdx int // 0=list, 1=preview

	// Overlays
	InputOverlay   *overlay.InputOverlay
	ConfirmOverlay *overlay.ConfirmOverlay

	// Lifecycle
	Ready bool
	Err   error
}

// Message types for BubbleTea
type (
	eventMsg    event.Event
	tickMsg     time.Time
	errMsg      error
)

// NewModel creates a new TUI model.
func NewModel(mgr *session.SessionManager, bus event.Bus) Model {
	eventCh := bus.Subscribe(
		event.SessionCreated,
		event.SessionStarted,
		event.SessionStatusChanged,
		event.SessionOutputChanged,
		event.SessionCompleted,
		event.SessionFailed,
		event.MetricsUpdated,
	)

	return Model{
		Manager:  mgr,
		EventBus: bus,
		EventCh:  eventCh,
		Keys:     DefaultKeyMap(),
		Sessions: mgr.List(),
	}
}

// Init initializes the BubbleTea program.
func (m Model) Init() tea.Cmd {
	return tea.Batch(
		m.listenEvents(),
		m.tick(),
	)
}

// Update handles messages.
func (m Model) Update(msg tea.Msg) (tea.Model, tea.Cmd) {
	switch msg := msg.(type) {
	case tea.WindowSizeMsg:
		m.Layout = ComputeLayout(msg.Width, msg.Height)
		m.Ready = true
		return m, nil

	case tickMsg:
		m.refreshSessions()
		m.refreshPreview()
		return m, m.tick()

	case eventMsg:
		m.refreshSessions()
		m.refreshPreview()
		if msg.Type == event.MetricsUpdated {
			if snap, ok := msg.Data.(monitor.Snapshot); ok {
				if m.selectedSession() != nil && snap.SessionID == m.selectedSession().ID {
					m.Snapshot = snap
				}
			}
		}
		return m, m.listenEvents()

	case errMsg:
		m.Err = msg
		return m, nil

	case tea.KeyMsg:
		return m.handleKey(msg)
	}

	return m, nil
}

// View renders the UI.
func (m Model) View() string {
	if !m.Ready {
		return "Loading..."
	}

	// Header
	header := titleStyle.Render("─ Agent Forge ─")

	// Session list
	sl := &SessionList{
		Sessions: m.Sessions,
		Selected: m.Selected,
		Width:    m.Layout.ListWidth,
		Height:   m.Layout.ListHeight,
		Active:   m.FocusIdx == 0,
	}

	// Preview panel
	pv := &Preview{
		Content: m.Preview,
		Width:   m.Layout.PreviewWidth,
		Height:  m.Layout.PreviewHeight,
		Active:  m.FocusIdx == 1,
	}
	if sess := m.selectedSession(); sess != nil {
		pv.Title = sess.Title
	}

	// Monitor panel
	mp := &MonitorPanel{
		Session:  m.selectedSession(),
		Snapshot: m.Snapshot,
		Width:    m.Layout.MonitorWidth,
		Height:   m.Layout.MonitorHeight,
	}

	// Menu
	menu := &Menu{Width: m.Layout.MenuWidth}

	// Compose layout
	panels := lipgloss.JoinHorizontal(lipgloss.Top, sl.View(), pv.View())
	mainView := lipgloss.JoinVertical(lipgloss.Left,
		header,
		panels,
		mp.View(),
		menu.View(),
	)

	// Overlay
	switch m.Mode {
	case ModeNewSession:
		if m.InputOverlay != nil {
			return placeOverlay(mainView, m.InputOverlay.View(), m.Layout.Width, m.Layout.Height)
		}
	case ModeConfirmKill:
		if m.ConfirmOverlay != nil {
			return placeOverlay(mainView, m.ConfirmOverlay.View(), m.Layout.Width, m.Layout.Height)
		}
	case ModeHelp:
		helpView := (&overlay.HelpOverlay{Width: 50}).View()
		return placeOverlay(mainView, helpView, m.Layout.Width, m.Layout.Height)
	}

	// Error display
	if m.Err != nil {
		errLine := lipgloss.NewStyle().Foreground(colorDanger).Render(fmt.Sprintf(" Error: %v", m.Err))
		mainView = strings.TrimRight(mainView, "\n") + "\n" + errLine
	}

	return mainView
}

func (m Model) handleKey(msg tea.KeyMsg) (tea.Model, tea.Cmd) {
	// Handle overlay modes first
	switch m.Mode {
	case ModeNewSession:
		if m.InputOverlay != nil {
			cmd := m.InputOverlay.Update(msg)
			if m.InputOverlay.Submitted {
				title := m.InputOverlay.Value()
				m.Mode = ModeNormal
				m.InputOverlay = nil
				if title != "" {
					_, err := m.Manager.Create(session.SessionConfig{Title: title})
					if err != nil {
						m.Err = err
					}
					m.refreshSessions()
				}
				return m, nil
			}
			if m.InputOverlay.Cancelled {
				m.Mode = ModeNormal
				m.InputOverlay = nil
				return m, nil
			}
			return m, cmd
		}

	case ModeConfirmKill:
		switch msg.String() {
		case "y":
			if sess := m.selectedSession(); sess != nil {
				if err := m.Manager.Kill(sess.ID); err != nil {
					m.Err = err
				}
				m.refreshSessions()
			}
			m.Mode = ModeNormal
			m.ConfirmOverlay = nil
			return m, nil
		case "n", "esc":
			m.Mode = ModeNormal
			m.ConfirmOverlay = nil
			return m, nil
		}
		return m, nil

	case ModeHelp:
		if msg.String() == "?" || msg.String() == "esc" || msg.String() == "q" {
			m.Mode = ModeNormal
			return m, nil
		}
		return m, nil
	}

	// Normal mode keys
	switch {
	case key.Matches(msg, m.Keys.Quit):
		return m, tea.Quit

	case key.Matches(msg, m.Keys.Up):
		if m.Selected > 0 {
			m.Selected--
			m.refreshPreview()
		}

	case key.Matches(msg, m.Keys.Down):
		if m.Selected < len(m.Sessions)-1 {
			m.Selected++
			m.refreshPreview()
		}

	case key.Matches(msg, m.Keys.New):
		ov := overlay.NewInputOverlay("New Session", "session title...", 50)
		m.InputOverlay = &ov
		m.Mode = ModeNewSession
		return m, m.InputOverlay.Input.Focus()

	case key.Matches(msg, m.Keys.Pause):
		if sess := m.selectedSession(); sess != nil {
			if err := m.Manager.Pause(sess.ID); err != nil {
				m.Err = err
			}
			m.refreshSessions()
		}

	case key.Matches(msg, m.Keys.Resume):
		if sess := m.selectedSession(); sess != nil {
			if err := m.Manager.Resume(sess.ID); err != nil {
				m.Err = err
			}
			m.refreshSessions()
		}

	case key.Matches(msg, m.Keys.Kill):
		if sess := m.selectedSession(); sess != nil {
			ov := overlay.NewConfirmOverlay(
				"Kill Session",
				fmt.Sprintf("Kill session %q?", sess.Title),
				50,
			)
			m.ConfirmOverlay = &ov
			m.Mode = ModeConfirmKill
		}

	case key.Matches(msg, m.Keys.Tab):
		m.FocusIdx = (m.FocusIdx + 1) % 2

	case key.Matches(msg, m.Keys.Help):
		m.Mode = ModeHelp

	case key.Matches(msg, m.Keys.Enter):
		if sess := m.selectedSession(); sess != nil {
			if sess.Status == session.StatusCreating {
				if err := m.Manager.Start(sess.ID); err != nil {
					m.Err = err
				}
				m.refreshSessions()
			}
		}
	}

	return m, nil
}

func (m *Model) refreshSessions() {
	m.Sessions = m.Manager.List()
	if m.Selected >= len(m.Sessions) && len(m.Sessions) > 0 {
		m.Selected = len(m.Sessions) - 1
	}
}

func (m *Model) refreshPreview() {
	sess := m.selectedSession()
	if sess == nil {
		m.Preview = ""
		return
	}

	output, err := m.Manager.CaptureOutput(sess.ID)
	if err != nil {
		m.Preview = mutedStyle.Render(fmt.Sprintf("(%s)", sess.Status))
		return
	}
	m.Preview = output

	if snap, ok := m.Manager.GetMetricsSnapshot(sess.ID); ok {
		m.Snapshot = snap
	}
}

func (m Model) selectedSession() *session.Session {
	if m.Selected < 0 || m.Selected >= len(m.Sessions) {
		return nil
	}
	return m.Sessions[m.Selected]
}

func (m Model) listenEvents() tea.Cmd {
	return func() tea.Msg {
		evt, ok := <-m.EventCh
		if !ok {
			return nil
		}
		return eventMsg(evt)
	}
}

func (m Model) tick() tea.Cmd {
	return tea.Tick(200*time.Millisecond, func(t time.Time) tea.Msg {
		return tickMsg(t)
	})
}

// placeOverlay centers an overlay on top of the background view.
func placeOverlay(bg, fg string, width, height int) string {
	return lipgloss.Place(
		width, height,
		lipgloss.Center, lipgloss.Center,
		fg,
		lipgloss.WithWhitespaceChars(" "),
	)
}
