package overlay

import "github.com/charmbracelet/lipgloss"

// ConfirmOverlay is a yes/no confirmation dialog.
type ConfirmOverlay struct {
	Title   string
	Message string
	Width   int
	Result  *bool // nil = pending, true = yes, false = no
}

// NewConfirmOverlay creates a new confirmation overlay.
func NewConfirmOverlay(title, message string, width int) ConfirmOverlay {
	return ConfirmOverlay{
		Title:   title,
		Message: message,
		Width:   width,
	}
}

// View renders the confirmation overlay.
func (c *ConfirmOverlay) View() string {
	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#EF4444")).Render(c.Title)
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Render("[y] Yes  [n/Esc] No")

	content := title + "\n\n" + c.Message + "\n\n" + hint

	return overlayStyle.Width(c.Width).Render(content)
}
