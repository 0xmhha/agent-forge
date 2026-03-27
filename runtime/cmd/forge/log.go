package main

import (
	"fmt"

	"github.com/spf13/cobra"
)

var logFlags struct {
	follow bool
}

var logCmd = &cobra.Command{
	Use:   "log <id|title>",
	Short: "Show session output",
	Args:  cobra.ExactArgs(1),
	RunE:  runLog,
}

func init() {
	logCmd.Flags().BoolVarP(&logFlags.follow, "follow", "f", false, "follow output (live)")

	rootCmd.AddCommand(logCmd)
}

func runLog(cmd *cobra.Command, args []string) error {
	sess, err := resolveSession(args[0])
	if err != nil {
		return err
	}

	output, err := mgr.CaptureOutput(sess.ID)
	if err != nil {
		return fmt.Errorf("failed to capture output: %w", err)
	}

	if output == "" {
		fmt.Printf("(no output for session %s)\n", sess.Title)
		return nil
	}

	fmt.Println(output)
	return nil
}
