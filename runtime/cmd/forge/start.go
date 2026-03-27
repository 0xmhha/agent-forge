package main

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/terminal"
)

var startCmd = &cobra.Command{
	Use:   "start <id|title>",
	Short: "Start a created session (launch Claude Code in tmux)",
	Args:  cobra.ExactArgs(1),
	RunE:  runStart,
}

func init() {
	rootCmd.AddCommand(startCmd)
}

func runStart(cmd *cobra.Command, args []string) error {
	sess, err := resolveSession(args[0])
	if err != nil {
		return err
	}

	if err := mgr.Start(sess.ID); err != nil {
		return err
	}

	tmuxName := terminal.SessionName(sess.ID)
	fmt.Printf("Session started: %s\n", sess.ID[:8])
	fmt.Printf("  tmux: %s\n", tmuxName)

	return nil
}
