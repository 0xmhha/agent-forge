package overlay

import (
	"github.com/charmbracelet/bubbles/textinput"
	tea "github.com/charmbracelet/bubbletea"
	"github.com/charmbracelet/lipgloss"
)

var overlayStyle = lipgloss.NewStyle().
	Border(lipgloss.DoubleBorder()).
	BorderForeground(lipgloss.Color("#7C3AED")).
	Padding(1, 2)

// InputOverlay is a text input dialog.
type InputOverlay struct {
	Title    string
	Input    textinput.Model
	Width    int
	Submitted bool
	Cancelled bool
}

// NewInputOverlay creates a new input overlay.
func NewInputOverlay(title, placeholder string, width int) InputOverlay {
	ti := textinput.New()
	ti.Placeholder = placeholder
	ti.Focus()
	ti.Width = width - 10

	return InputOverlay{
		Title: title,
		Input: ti,
		Width: width,
	}
}

// Update handles input events.
func (o *InputOverlay) Update(msg tea.Msg) tea.Cmd {
	switch msg := msg.(type) {
	case tea.KeyMsg:
		switch msg.String() {
		case "enter":
			o.Submitted = true
			return nil
		case "esc":
			o.Cancelled = true
			return nil
		}
	}

	var cmd tea.Cmd
	o.Input, cmd = o.Input.Update(msg)
	return cmd
}

// View renders the input overlay.
func (o *InputOverlay) View() string {
	title := lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#7C3AED")).Render(o.Title)
	hint := lipgloss.NewStyle().Foreground(lipgloss.Color("#6B7280")).Render("Enter to submit, Esc to cancel")

	content := title + "\n\n" + o.Input.View() + "\n\n" + hint

	return overlayStyle.Width(o.Width).Render(content)
}

// Value returns the current input value.
func (o *InputOverlay) Value() string {
	return o.Input.Value()
}
