package terminal

import "crypto/sha256"

// OutputTracker detects changes in terminal output via SHA-256 hashing.
type OutputTracker struct {
	lastHash [32]byte
}

// HasChanged returns true if the output has changed since last check.
func (t *OutputTracker) HasChanged(currentOutput string) bool {
	hash := sha256.Sum256([]byte(currentOutput))
	changed := hash != t.lastHash
	t.lastHash = hash
	return changed
}
