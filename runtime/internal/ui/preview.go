package ui

import (
	"strings"

	"github.com/charmbracelet/lipgloss"
)

// Preview renders the terminal output preview panel.
type Preview struct {
	Content string
	Title   string
	Width   int
	Height  int
	Active  bool
}

// View renders the preview panel.
func (p *Preview) View() string {
	style := borderStyle
	if p.Active {
		style = activeBorderStyle
	}

	title := titleStyle.Render(" Preview")
	if p.Title != "" {
		title = titleStyle.Render(" " + p.Title)
	}

	// Trim content to fit
	contentHeight := p.Height - 2
	lines := strings.Split(p.Content, "\n")

	// Show last N lines (tail behavior)
	if len(lines) > contentHeight {
		lines = lines[len(lines)-contentHeight:]
	}

	// Pad to fill
	for len(lines) < contentHeight {
		lines = append(lines, "")
	}

	// Truncate each line to width
	contentWidth := p.Width - 2
	for i, line := range lines {
		if len(line) > contentWidth {
			lines[i] = line[:contentWidth]
		} else {
			lines[i] = line + strings.Repeat(" ", contentWidth-lipgloss.Width(line))
		}
	}

	content := mutedStyle.Render(strings.Join(lines, "\n"))

	return style.
		Width(p.Width).
		Height(p.Height).
		Render(title + "\n" + content)
}
