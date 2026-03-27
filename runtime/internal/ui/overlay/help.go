package overlay

import "github.com/charmbracelet/lipgloss"

// HelpOverlay displays key bindings help.
type HelpOverlay struct {
	Width int
}

// View renders the help overlay.
func (h *HelpOverlay) View() string {
	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#7C3AED")).Render("Key Bindings")

	keyStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#A78BFA")).Bold(true).Width(12)
	descStyle := lipgloss.NewStyle().Foreground(lipgloss.Color("#D1D5DB"))

	bindings := []struct{ key, desc string }{
		{"↑/k", "Previous session"},
		{"↓/j", "Next session"},
		{"Enter/o", "Attach to session"},
		{"n", "New session"},
		{"p", "Pause session"},
		{"r", "Resume session"},
		{"D", "Kill session"},
		{"Tab", "Switch panel focus"},
		{"Ctrl+Q", "Detach (in attach mode)"},
		{"q", "Quit"},
		{"?", "Toggle help"},
	}

	content := title + "\n\n"
	for _, b := range bindings {
		content += keyStyle.Render(b.key) + descStyle.Render(b.desc) + "\n"
	}

	content += "\n" + lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Render("Press ? or Esc to close")

	return overlayStyle.Width(h.Width).Render(content)
}
