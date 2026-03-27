package ui

// Layout holds computed dimensions for each UI region.
type Layout struct {
	// Total
	Width  int
	Height int

	// Session list (left panel)
	ListWidth  int
	ListHeight int

	// Preview (right panel, main area)
	PreviewWidth  int
	PreviewHeight int

	// Monitor bar (below panels)
	MonitorWidth  int
	MonitorHeight int

	// Menu bar (bottom)
	MenuWidth int
}

// ComputeLayout calculates dimensions based on terminal size.
func ComputeLayout(width, height int) Layout {
	const (
		listWidthRatio = 0.25
		minListWidth   = 20
		maxListWidth   = 35
		monitorHeight  = 3
		menuHeight     = 1
		headerHeight   = 1
	)

	// List width: 25% of total, clamped
	listWidth := int(float64(width) * listWidthRatio)
	if listWidth < minListWidth {
		listWidth = minListWidth
	}
	if listWidth > maxListWidth {
		listWidth = maxListWidth
	}

	previewWidth := width - listWidth

	// Vertical: header + panels + monitor + menu
	panelHeight := height - headerHeight - monitorHeight - menuHeight
	if panelHeight < 5 {
		panelHeight = 5
	}

	return Layout{
		Width:         width,
		Height:        height,
		ListWidth:     listWidth,
		ListHeight:    panelHeight,
		PreviewWidth:  previewWidth,
		PreviewHeight: panelHeight,
		MonitorWidth:  width,
		MonitorHeight: monitorHeight,
		MenuWidth:     width,
	}
}
