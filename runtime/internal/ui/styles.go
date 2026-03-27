package ui

import "github.com/charmbracelet/lipgloss"

var (
	// Colors
	colorPrimary   = lipgloss.Color("#7C3AED")
	colorSecondary = lipgloss.Color("#6B7280")
	colorSuccess   = lipgloss.Color("#10B981")
	colorWarning   = lipgloss.Color("#F59E0B")
	colorDanger    = lipgloss.Color("#EF4444")
	colorMuted     = lipgloss.Color("#4B5563")
	colorHighlight = lipgloss.Color("#A78BFA")

	// Base styles
	titleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(colorPrimary)

	borderStyle = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(colorMuted)

	activeBorderStyle = lipgloss.NewStyle().
				Border(lipgloss.RoundedBorder()).
				BorderForeground(colorPrimary)

	selectedStyle = lipgloss.NewStyle().
			Background(lipgloss.Color("#1F2937")).
			Foreground(lipgloss.Color("#F9FAFB")).
			Bold(true)

	mutedStyle = lipgloss.NewStyle().
			Foreground(colorMuted)

	menuKeyStyle = lipgloss.NewStyle().
			Foreground(colorHighlight).
			Bold(true)

	menuDescStyle = lipgloss.NewStyle().
			Foreground(colorSecondary)

	statusRunning   = lipgloss.NewStyle().Foreground(colorSuccess)
	statusWaiting   = lipgloss.NewStyle().Foreground(colorWarning)
	statusPaused    = lipgloss.NewStyle().Foreground(colorSecondary)
	statusCompleted = lipgloss.NewStyle().Foreground(colorSuccess)
	statusFailed    = lipgloss.NewStyle().Foreground(colorDanger)
)
