package sandbox

import (
	"encoding/json"
	"fmt"
	"strings"
)

// settingsJSON represents the Claude Code settings.json structure.
type settingsJSON struct {
	Permissions permissionsJSON `json:"permissions"`
}

type permissionsJSON struct {
	Allow []string `json:"allow"`
	Deny  []string `json:"deny"`
}

// GenerateSettingsJSON converts a Policy into Claude Code settings.json content.
func GenerateSettingsJSON(policy Policy) ([]byte, error) {
	settings := settingsJSON{
		Permissions: permissionsJSON{
			Allow: permissionsToStrings(policy.Allow),
			Deny:  permissionsToStrings(policy.Deny),
		},
	}

	return json.MarshalIndent(settings, "", "  ")
}

// GenerateClaudeMD creates CLAUDE.md content for a sandbox session.
func GenerateClaudeMD(cfg ClaudeMDConfig) string {
	var b strings.Builder

	fmt.Fprintf(&b, "# Session: %s\n\n", cfg.Title)

	b.WriteString("## Task\n")
	b.WriteString(cfg.TaskPrompt)
	b.WriteString("\n\n")

	b.WriteString("## Constraints\n")

	if len(cfg.AllowedPaths) > 0 {
		fmt.Fprintf(&b, "- Allowed files: %s\n", strings.Join(cfg.AllowedPaths, ", "))
	}

	if cfg.TokenBudget > 0 {
		fmt.Fprintf(&b, "- Token budget: %d tokens\n", cfg.TokenBudget)
	}

	if cfg.NetworkAccess {
		b.WriteString("- Network access: allowed\n")
	} else {
		b.WriteString("- Network access: blocked\n")
	}

	b.WriteString("- This session performs only the specified task.\n")
	b.WriteString("- Summarize results and exit upon completion.\n\n")

	b.WriteString("## Working Directory\n")
	b.WriteString("This directory is the working root.\n")
	b.WriteString("Do not access parent directories.\n")

	if cfg.Instructions != "" {
		b.WriteString("\n## Additional Instructions\n")
		b.WriteString(cfg.Instructions)
		b.WriteString("\n")
	}

	return b.String()
}

// ClaudeMDConfig holds parameters for generating CLAUDE.md.
type ClaudeMDConfig struct {
	Title         string
	TaskPrompt    string
	AllowedPaths  []string
	TokenBudget   int64
	NetworkAccess bool
	Instructions  string
}

// permissionsToStrings converts Permission structs to Claude Code format strings.
// Example: Permission{Tool: "Bash", Pattern: "npm test"} → "Bash(npm test)"
func permissionsToStrings(perms []Permission) []string {
	result := make([]string, 0, len(perms))
	for _, p := range perms {
		if p.Pattern != "" {
			result = append(result, fmt.Sprintf("%s(%s)", p.Tool, p.Pattern))
		} else {
			result = append(result, p.Tool)
		}
	}
	return result
}
