package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"

	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

// SessionList renders the session list panel.
type SessionList struct {
	Sessions []*session.Session
	Selected int
	Width    int
	Height   int
	Active   bool
}

// View renders the session list.
func (sl *SessionList) View() string {
	var b strings.Builder

	headerStyle := borderStyle
	if sl.Active {
		headerStyle = activeBorderStyle
	}

	// Render items
	contentHeight := sl.Height - 2 // borders
	for i, sess := range sl.Sessions {
		if i >= contentHeight {
			break
		}

		icon := sessionIcon(sess.Status)
		line := fmt.Sprintf(" %s %s", icon, truncate(sess.Title, sl.Width-6))

		if i == sl.Selected {
			line = selectedStyle.Width(sl.Width - 2).Render(line)
		} else {
			line = lipgloss.NewStyle().Width(sl.Width - 2).Render(line)
		}

		b.WriteString(line)
		b.WriteString("\n")
	}

	// Pad remaining space
	rendered := b.String()
	lines := strings.Count(rendered, "\n")
	for i := lines; i < contentHeight; i++ {
		rendered += strings.Repeat(" ", sl.Width-2) + "\n"
	}

	return headerStyle.
		Width(sl.Width).
		Height(sl.Height).
		Render(titleStyle.Render(" Sessions") + "\n" + rendered)
}

func sessionIcon(s session.Status) string {
	switch s {
	case session.StatusRunning:
		return statusRunning.Render("●")
	case session.StatusWaiting:
		return statusWaiting.Render("✱")
	case session.StatusPaused:
		return statusPaused.Render("⏸")
	case session.StatusCompleted:
		return statusCompleted.Render("✓")
	case session.StatusFailed:
		return statusFailed.Render("✗")
	default:
		return mutedStyle.Render("○")
	}
}

func truncate(s string, maxLen int) string {
	if maxLen <= 0 {
		return ""
	}
	if len(s) <= maxLen {
		return s
	}
	if maxLen <= 3 {
		return s[:maxLen]
	}
	return s[:maxLen-3] + "..."
}
