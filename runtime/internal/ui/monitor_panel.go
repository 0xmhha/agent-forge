package ui

import (
	"fmt"
	"strings"
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/monitor"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

// MonitorPanel renders session metrics.
type MonitorPanel struct {
	Session  *session.Session
	Snapshot monitor.Snapshot
	Width    int
	Height   int
}

// View renders the monitor panel.
func (mp *MonitorPanel) View() string {
	if mp.Session == nil {
		return borderStyle.Width(mp.Width).Height(mp.Height).Render(
			mutedStyle.Render(" No session selected"),
		)
	}

	var b strings.Builder

	// Left side: CPU/Mem
	cpu := fmt.Sprintf("CPU: %.0f%%", mp.Snapshot.CPUPercent)
	mem := fmt.Sprintf("Mem: %.0f MB", mp.Snapshot.MemoryMB)
	b.WriteString(fmt.Sprintf(" %s  │ %s", cpu, mem))

	// Right side: Tokens/Duration
	if mp.Snapshot.TokensUsed > 0 {
		b.WriteString(fmt.Sprintf("  │ Tokens: %s", formatNumber(mp.Snapshot.TokensUsed)))
	}

	if !mp.Session.StartedAt.IsZero() && mp.Session.Status == session.StatusRunning {
		dur := time.Since(mp.Session.StartedAt).Truncate(time.Second)
		b.WriteString(fmt.Sprintf("  │ %s", dur))
	}

	return borderStyle.Width(mp.Width).Height(mp.Height).Render(
		mutedStyle.Render(b.String()),
	)
}

func formatNumber(n int64) string {
	s := fmt.Sprintf("%d", n)
	if n < 1000 {
		return s
	}

	var result []byte
	for i, c := range s {
		if i > 0 && (len(s)-i)%3 == 0 {
			result = append(result, ',')
		}
		result = append(result, byte(c))
	}
	return string(result)
}
