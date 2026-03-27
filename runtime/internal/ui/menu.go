package ui

import "strings"

// Menu renders the bottom key bindings bar.
type Menu struct {
	Width   int
	Attach  bool // true when in attach mode
}

// View renders the menu bar.
func (m *Menu) View() string {
	if m.Attach {
		return menuKeyStyle.Render("[Ctrl+Q]") + menuDescStyle.Render("Detach")
	}

	items := []struct{ key, desc string }{
		{"n", "New"},
		{"Enter", "Attach"},
		{"p", "Pause"},
		{"r", "Resume"},
		{"D", "Kill"},
		{"?", "Help"},
		{"q", "Quit"},
	}

	var parts []string
	for _, item := range items {
		parts = append(parts,
			menuKeyStyle.Render("["+item.key+"]")+menuDescStyle.Render(item.desc),
		)
	}

	line := strings.Join(parts, " ")

	return line
}
