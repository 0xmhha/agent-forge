package main

import (
	"fmt"
	"os"

	tea "github.com/charmbracelet/bubbletea"
	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/config"
	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
	"github.com/agent-forge/agent-forge/runtime/internal/ui"
)

var (
	version = "dev"
	commit  = "none"
)

var (
	cfg    *config.Config
	mgr    *session.SessionManager
	evtBus event.Bus
)

var rootCmd = &cobra.Command{
	Use:   "forge",
	Short: "Agent Forge — AI session manager",
	Long:  "Manage isolated Claude Code sessions with sandboxing, monitoring, and TUI.",
	PersistentPreRunE: func(cmd *cobra.Command, args []string) error {
		if cmd.Name() == "version" {
			return nil
		}

		var err error
		cfg, err = config.Load()
		if err != nil {
			return fmt.Errorf("failed to load config: %w", err)
		}

		if err := cfg.Paths.EnsureDirs(); err != nil {
			return err
		}

		evtBus = event.NewChannelBus(64)
		store := session.NewFileStore(cfg.Paths.State)
		mgr = session.NewSessionManager(cfg, store, evtBus)

		if err := mgr.Restore(); err != nil {
			fmt.Fprintf(os.Stderr, "warning: session restore failed: %v\n", err)
		}

		return nil
	},
	RunE: func(cmd *cobra.Command, args []string) error {
		// Launch TUI when no subcommand is specified
		mgr.StartLoops()
		defer mgr.StopLoops()

		model := ui.NewModel(mgr, evtBus)
		p := tea.NewProgram(model, tea.WithAltScreen())
		_, err := p.Run()
		return err
	},
}

var versionCmd = &cobra.Command{
	Use:   "version",
	Short: "Print version information",
	Run: func(cmd *cobra.Command, args []string) {
		fmt.Printf("forge %s (commit: %s)\n", version, commit)
	},
}

func init() {
	rootCmd.AddCommand(versionCmd)
}

func main() {
	if err := rootCmd.Execute(); err != nil {
		os.Exit(1)
	}
}
