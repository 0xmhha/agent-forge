package session

import "errors"

// Transition defines a state transition rule.
type Transition struct {
	From  Status
	To    Status
	Guard func(s *Session) error
}

var transitions = []Transition{
	{From: StatusCreating, To: StatusRunning, Guard: guardCreatingToRunning},
	{From: StatusRunning, To: StatusWaiting},
	{From: StatusWaiting, To: StatusRunning},
	{From: StatusRunning, To: StatusPaused},
	{From: StatusWaiting, To: StatusPaused},
	{From: StatusPaused, To: StatusRunning, Guard: guardPausedToRunning},
	{From: StatusRunning, To: StatusCompleted},
	{From: StatusCreating, To: StatusFailed},
	{From: StatusRunning, To: StatusFailed},
	{From: StatusWaiting, To: StatusFailed},
}

func guardCreatingToRunning(s *Session) error {
	if s.SandboxDir == "" {
		return errors.New("sandbox not initialized")
	}
	return nil
}

func guardPausedToRunning(s *Session) error {
	if s.SandboxDir == "" {
		return errors.New("sandbox directory missing")
	}
	return nil
}

// ValidateTransition checks if a state transition is allowed.
func ValidateTransition(from, to Status) *Transition {
	for i := range transitions {
		if transitions[i].From == from && transitions[i].To == to {
			return &transitions[i]
		}
	}
	return nil
}
