package main

import (
	"fmt"
	"os"

	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

var attachCmd = &cobra.Command{
	Use:   "attach <id|title>",
	Short: "Attach to a running session (interactive mode)",
	Args:  cobra.ExactArgs(1),
	RunE:  runAttach,
}

func init() {
	rootCmd.AddCommand(attachCmd)
}

func runAttach(cmd *cobra.Command, args []string) error {
	sess, err := resolveSession(args[0])
	if err != nil {
		return err
	}

	if sess.Status != session.StatusRunning && sess.Status != session.StatusWaiting {
		return fmt.Errorf("session %q is not running (status: %s)", sess.Title, sess.Status)
	}

	fmt.Printf("Attaching to %s (%s)... Press Ctrl+Q to detach\n", sess.Title, sess.ID[:8])

	doneCh, err := mgr.Attach(sess.ID, os.Stdin, os.Stdout)
	if err != nil {
		return fmt.Errorf("attach failed: %w", err)
	}

	// Block until detached
	<-doneCh
	fmt.Println("\nDetached.")

	return nil
}
