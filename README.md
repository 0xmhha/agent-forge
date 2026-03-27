# Agent Forge

A methodology framework and session runtime for LLM-based software development.

Agent Forge has two components:

- **Methodology** — Claude Code skills that enforce plan-execute-review workflows with quality gates
- **Runtime** (`forge`) — A Go CLI/TUI that manages isolated Claude Code sessions with sandboxing, monitoring, and background execution

## Quick Start

### Methodology Skills (for any Claude Code project)

```bash
# Install core skills to your project
./dist/install.sh /path/to/your-project

# Include review skills (Gmail + GitHub integration)
./dist/install.sh /path/to/your-project --full

# Global install (applies to all projects)
./dist/install.sh /path/to/your-project --global
```

After installation, use the workflow in Claude Code:

```
/complexity    →  assess task, pick tier  →  code  →  /milestone
```

### Runtime (forge CLI)

```bash
# Build
cd runtime && go build -o forge ./cmd/forge

# Launch TUI
./forge

# Or use CLI commands
./forge new "refactor auth" --task "Refactor auth middleware" --policy restricted
./forge start refactor
./forge list
./forge attach refactor
```

## Methodology

### Workflow Tiers

Every task starts with `/complexity` to determine the appropriate verification level:

| Tier | Files | Process |
|------|-------|---------|
| **Micro** | 1-2 | Execute directly, commit |
| **Standard** | 3-10 | Plan → Execute → QR gate → Handoff → Commit |
| **Full** | 10+ | Auto-decompose into milestones → Per-milestone (Execute → QR) → Handoff → Commit |

### Skills

| Command | Purpose |
|---------|---------|
| `/complexity` | Assess complexity, recommend tier, auto-decompose for Full tier |
| `/qr-gate` | Quality review with auto-fix loop (MUST/SHOULD/COULD severity, max 2 iterations) |
| `/delta-log` | Record milestone context (delta entry + rolling summary) |
| `/milestone` | Run complete workflow: QR → delta-log → handoff → token collection → commit |
| `/handoff` | Generate session handoff document for context transfer |

Review skills (installed with `--full`):

| Command | Purpose |
|---------|---------|
| `/check-reviews` | Collect pending reviews from Gmail + GitHub in parallel |
| `/do-review` | Execute code review via sub-agent |

### Methodology Phases

The methodology is built in four layers, each adding capabilities on top of the previous:

```
Phase 1: Process Model ──────── Done
         QR gates, temporal rules, workflow tiers, convention layers

Phase 2: Domain Profiles ────── Done
         YAML schema, 3 example profiles (fintech, game-dev, startup-mvp)

Phase 3: Context Management ─── Done
         delta-log system, rolling-summary, merge rules

Phase 4: Measurement ────────── Design complete (awaiting data collection)
         17 metrics, collection guide, analysis playbook
```

## Runtime (`forge`)

The runtime manages Claude Code sessions in isolated tmux environments with security policies, resource monitoring, and a TUI dashboard.

### Requirements

- Go 1.24+
- tmux 3.0+
- Claude CLI

### Build

```bash
cd runtime
go build -o forge ./cmd/forge
```

### CLI Commands

```bash
# Session management
forge new <title> [flags]       # Create a new session
  --task "description"          #   Task for the AI
  --policy restricted           #   Security policy: readonly/restricted/standard/full
  --project /path/to/project    #   Target project path
  --budget 50000                #   Token budget (0 = unlimited)
forge start <id|title>          # Start session (launch Claude Code in tmux)
forge list                      # List all sessions
forge status [id|title]         # Show status and metrics
forge attach <id|title>         # Interactive terminal connection
forge pause <id|title>          # Pause a running session
forge resume <id|title>         # Resume a paused session
forge kill <id|title>           # Terminate and clean up
forge log <id|title>            # Show session output

# TUI
forge                           # Launch interactive TUI (default)

# Background daemon
forge daemon start              # Start background session monitor
forge daemon stop               # Stop daemon
forge daemon status             # Check daemon status

# Configuration
forge config                    # Show current configuration
forge version                   # Print version
```

### Security Policies

Each session runs in a sandbox with a security policy that controls which Claude Code tools are allowed:

| Preset | Allowed Tools | Use Case |
|--------|--------------|----------|
| `readonly` | Read, Glob, Grep | Analysis without modifications |
| `restricted` | + Write, Edit | Limited writes, no shell |
| `standard` | + Bash (npm test, go test, git diff) | General development |
| `full` | All tools including Bash, Agent | Trusted tasks |

### Session Lifecycle

```
Creating → Running ⇄ Waiting → Completed
              ↓          ↓
           Paused ←──────┘      Failed
```

- **Creating**: Sandbox configured, waiting for `start`
- **Running**: Claude Code actively working
- **Waiting**: Claude Code awaiting user input
- **Paused**: Terminal detached, sandbox preserved
- **Completed/Failed**: Terminal state

### TUI Key Bindings

```
↑/k          Previous session          n        New session
↓/j          Next session              p        Pause
Enter/o      Attach (interactive)      r        Resume
Tab          Switch panel focus         D        Kill (with confirmation)
?            Help                       q        Quit
Ctrl+Q       Detach (in attach mode)
```

## MCP Tools

### workspace-mcp (24 tools)

Gmail + GitHub monitoring and code review automation.

| Category | Tools | Features |
|----------|-------|----------|
| Gmail | 5 | Mail listing, search, Jira ticket detection, action classification |
| GitHub | 7 | Issues/PRs, CI status, PR review environment setup |
| Review | 9 | Pending/done review management, todo creation, agent polling |
| Task | 3 | Task list, sync, status updates |

### token-monitor-mcp (5 tools)

Token usage tracking and cost analysis.

| Tool | Purpose |
|------|---------|
| `token_session_list` | List all sessions |
| `token_session_summary` | Per-session token details |
| `token_cost_check` | USD cost lookup |
| `token_session_export` | Export in agent-forge format |
| `token_monitor_version` | Binary version |

## Project Structure

```
agent-forge/
├── dist/                              Distributable (install to target projects)
│   ├── install.sh                     Installation script
│   ├── skills/                        7 skills
│   └── hooks/                         Pre-commit QR, session-end checklist
│
├── runtime/                           Go module — forge CLI + TUI
│   ├── cmd/forge/                     CLI entry point (10 command files)
│   └── internal/
│       ├── session/                   Session manager + state machine
│       ├── sandbox/                   Security policies + settings.json generation
│       ├── terminal/                  tmux-based terminal management
│       ├── monitor/                   CPU/Mem/Token metrics (gopsutil)
│       ├── event/                     EventBus (channel-based pub/sub)
│       ├── daemon/                    Background daemon + worker
│       ├── config/                    App configuration (~/.forge/)
│       └── ui/                        BubbleTea TUI + overlay dialogs
│
├── phases/                            Methodology documentation (Phase 1-4)
├── tools/                             MCP server implementations (Python)
├── delta-logs/                        Project milestone records
└── docs/                              Design documents
    ├── PHASE1-CORE-ENGINE.md          Runtime design specification
    ├── VISION-v2.md                   Full vision (5-layer architecture)
    ├── ARCHITECTURE.md                v1 methodology architecture
    └── ROADMAP.md                     Execution roadmap
```

## Development

```bash
# Runtime — build and test
cd runtime
go build ./cmd/forge
go test ./...
go vet ./...

# MCP tools — test
cd tools/workspace-mcp && uv run python -m pytest -q
cd tools/token-monitor-mcp && uv run python -m pytest -q

# MCP tools — run server
cd tools/workspace-mcp && make server

# OAuth setup (first time)
cd tools/workspace-mcp && make setup
```

## Documentation

| Document | Content |
|----------|---------|
| [PHASE1-CORE-ENGINE.md](docs/PHASE1-CORE-ENGINE.md) | Runtime design: package structure, interfaces, state machine, sandbox model |
| [VISION-v2.md](docs/VISION-v2.md) | Long-term vision: 5-layer architecture, browser metaphor, roadmap |
| [ARCHITECTURE.md](docs/ARCHITECTURE.md) | v1 methodology architecture |
| [ROADMAP.md](docs/ROADMAP.md) | Phase 1-4 execution roadmap |
| [ANALYSIS.md](docs/ANALYSIS.md) | Background research on LLM development approaches |
