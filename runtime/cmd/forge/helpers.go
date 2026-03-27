package main

import (
	"fmt"

	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

// resolveSession finds a session by full ID, prefix, or title.
func resolveSession(query string) (*session.Session, error) {
	sessions := mgr.List()

	// Exact ID match
	for _, s := range sessions {
		if s.ID == query {
			return s, nil
		}
	}

	// Prefix match
	var match *session.Session
	for _, s := range sessions {
		if len(query) <= len(s.ID) && s.ID[:len(query)] == query {
			if match != nil {
				return nil, fmt.Errorf("ambiguous session prefix: %q", query)
			}
			match = s
		}
	}
	if match != nil {
		return match, nil
	}

	// Title match
	for _, s := range sessions {
		if s.Title == query {
			return s, nil
		}
	}

	return nil, fmt.Errorf("session not found: %s", query)
}

func statusIcon(s session.Status) string {
	switch s {
	case session.StatusRunning:
		return "●"
	case session.StatusWaiting:
		return "✱"
	case session.StatusPaused:
		return "⏸"
	case session.StatusCompleted:
		return "✓"
	case session.StatusFailed:
		return "✗"
	default:
		return "○"
	}
}
