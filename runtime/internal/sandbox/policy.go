package sandbox

// Permission defines a Claude Code tool permission rule.
type Permission struct {
	Tool    string `json:"tool"`
	Pattern string `json:"pattern,omitempty"`
}

// Policy defines sandbox security rules.
type Policy struct {
	Name          string       `json:"name"`
	Description   string       `json:"description"`
	Allow         []Permission `json:"allow"`
	Deny          []Permission `json:"deny"`
	AllowedPaths  []string     `json:"allowed_paths,omitempty"`
	TokenBudget   int64        `json:"token_budget,omitempty"`
	NetworkAccess bool         `json:"network_access"`
	Instructions  string       `json:"instructions,omitempty"`
}
