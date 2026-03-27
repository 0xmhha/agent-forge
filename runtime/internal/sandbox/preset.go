package sandbox

// Presets contains predefined security policies.
var Presets = map[string]Policy{
	"readonly": {
		Name:        "readonly",
		Description: "Read-only analysis. No file modifications allowed.",
		Allow: []Permission{
			{Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
		},
		Deny: []Permission{
			{Tool: "Write"}, {Tool: "Edit"}, {Tool: "Bash"}, {Tool: "Agent"},
		},
		NetworkAccess: false,
	},

	"restricted": {
		Name:        "restricted",
		Description: "Limited write access. Shell execution blocked.",
		Allow: []Permission{
			{Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
			{Tool: "Write"}, {Tool: "Edit"},
		},
		Deny: []Permission{
			{Tool: "Bash"}, {Tool: "Agent"},
		},
		NetworkAccess: false,
	},

	"standard": {
		Name:        "standard",
		Description: "General development. Limited shell access.",
		Allow: []Permission{
			{Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
			{Tool: "Write"}, {Tool: "Edit"},
			{Tool: "Bash", Pattern: "npm test"},
			{Tool: "Bash", Pattern: "go test"},
			{Tool: "Bash", Pattern: "git diff"},
			{Tool: "Bash", Pattern: "git status"},
		},
		Deny: []Permission{
			{Tool: "Bash", Pattern: "rm -rf"},
			{Tool: "Bash", Pattern: "curl"},
			{Tool: "Bash", Pattern: "wget"},
			{Tool: "Agent"},
		},
		NetworkAccess: false,
	},

	"full": {
		Name:        "full",
		Description: "All tools allowed. For trusted tasks only.",
		Allow: []Permission{
			{Tool: "Read"}, {Tool: "Glob"}, {Tool: "Grep"},
			{Tool: "Write"}, {Tool: "Edit"}, {Tool: "Bash"},
			{Tool: "Agent"},
		},
		Deny:          []Permission{},
		NetworkAccess: true,
	},
}
