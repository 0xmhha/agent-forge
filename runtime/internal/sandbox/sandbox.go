package sandbox

import (
	"fmt"
	"os"
	"path/filepath"
)

// Sandbox represents an isolated execution environment for a session.
type Sandbox struct {
	ID          string
	RootDir     string
	Policy      Policy
	WorktreeDir string
}

// SandboxConfig holds parameters for setting up a sandbox.
type SandboxConfig struct {
	SessionID   string
	Title       string
	Policy      Policy
	ProjectPath string
	UseWorktree bool
	TaskPrompt  string
	SessionsDir string // parent directory for all session sandboxes
}

// Setup creates a sandbox directory and writes configuration files.
func Setup(cfg SandboxConfig) (*Sandbox, error) {
	if cfg.SessionID == "" {
		return nil, fmt.Errorf("session ID is required")
	}

	rootDir := filepath.Join(cfg.SessionsDir, cfg.SessionID)

	// Create sandbox directory structure
	claudeDir := filepath.Join(rootDir, ".claude")
	if err := os.MkdirAll(claudeDir, 0750); err != nil {
		return nil, fmt.Errorf("failed to create sandbox directory: %w", err)
	}

	// Generate and write settings.json
	settingsData, err := GenerateSettingsJSON(cfg.Policy)
	if err != nil {
		return nil, fmt.Errorf("failed to generate settings.json: %w", err)
	}

	settingsPath := filepath.Join(claudeDir, "settings.json")
	if err := os.WriteFile(settingsPath, settingsData, 0640); err != nil {
		return nil, fmt.Errorf("failed to write settings.json: %w", err)
	}

	// Generate and write CLAUDE.md
	claudeMD := GenerateClaudeMD(ClaudeMDConfig{
		Title:         cfg.Title,
		TaskPrompt:    cfg.TaskPrompt,
		AllowedPaths:  cfg.Policy.AllowedPaths,
		TokenBudget:   cfg.Policy.TokenBudget,
		NetworkAccess: cfg.Policy.NetworkAccess,
		Instructions:  cfg.Policy.Instructions,
	})

	claudeMDPath := filepath.Join(rootDir, "CLAUDE.md")
	if err := os.WriteFile(claudeMDPath, []byte(claudeMD), 0640); err != nil {
		return nil, fmt.Errorf("failed to write CLAUDE.md: %w", err)
	}

	// Write .gitignore
	gitignore := ".claude/\n"
	gitignorePath := filepath.Join(rootDir, ".gitignore")
	if err := os.WriteFile(gitignorePath, []byte(gitignore), 0640); err != nil {
		return nil, fmt.Errorf("failed to write .gitignore: %w", err)
	}

	return &Sandbox{
		ID:      cfg.SessionID,
		RootDir: rootDir,
		Policy:  cfg.Policy,
	}, nil
}

// Teardown removes the sandbox directory and all its contents.
func (s *Sandbox) Teardown() error {
	if s.RootDir == "" {
		return nil
	}
	return os.RemoveAll(s.RootDir)
}

// Preserve keeps the sandbox but cleans up temporary resources (e.g., worktree).
func (s *Sandbox) Preserve() error {
	if s.WorktreeDir == "" {
		return nil
	}

	// Remove worktree directory if it exists
	if err := os.RemoveAll(s.WorktreeDir); err != nil {
		return fmt.Errorf("failed to remove worktree: %w", err)
	}

	s.WorktreeDir = ""
	return nil
}
