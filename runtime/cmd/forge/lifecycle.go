package main

import (
	"fmt"
	"time"

	"github.com/spf13/cobra"
)

var pauseCmd = &cobra.Command{
	Use:   "pause <id|title>",
	Short: "Pause a running session",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		sess, err := resolveSession(args[0])
		if err != nil {
			return err
		}

		if err := mgr.Pause(sess.ID); err != nil {
			return err
		}

		fmt.Printf("Session paused: %s (%s)\n", sess.ID[:8], sess.Title)
		return nil
	},
}

var resumeCmd = &cobra.Command{
	Use:   "resume <id|title>",
	Short: "Resume a paused session",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		sess, err := resolveSession(args[0])
		if err != nil {
			return err
		}

		if err := mgr.Resume(sess.ID); err != nil {
			return err
		}

		fmt.Printf("Session resumed: %s (%s)\n", sess.ID[:8], sess.Title)
		return nil
	},
}

var killCmd = &cobra.Command{
	Use:   "kill <id|title>",
	Short: "Kill a session and clean up",
	Args:  cobra.ExactArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		sess, err := resolveSession(args[0])
		if err != nil {
			return err
		}

		if err := mgr.Kill(sess.ID); err != nil {
			return err
		}

		fmt.Printf("Session killed: %s (%s)\n", sess.ID[:8], sess.Title)
		return nil
	},
}

var statusCmd = &cobra.Command{
	Use:   "status [id|title]",
	Short: "Show session status and metrics",
	Args:  cobra.MaximumNArgs(1),
	RunE: func(cmd *cobra.Command, args []string) error {
		if len(args) == 0 {
			// Show all sessions summary
			sessions := mgr.List()
			counts := make(map[string]int)
			for _, s := range sessions {
				counts[s.Status.String()]++
			}
			fmt.Printf("Total sessions: %d\n", len(sessions))
			for status, count := range counts {
				fmt.Printf("  %s: %d\n", status, count)
			}
			return nil
		}

		sess, err := resolveSession(args[0])
		if err != nil {
			return err
		}

		fmt.Printf("Session: %s\n", sess.ID)
		fmt.Printf("  Title:    %s\n", sess.Title)
		fmt.Printf("  Status:   %s %s\n", statusIcon(sess.Status), sess.Status)
		fmt.Printf("  Policy:   %s\n", sess.PolicyName)
		fmt.Printf("  Sandbox:  %s\n", sess.SandboxDir)
		fmt.Printf("  Created:  %s\n", sess.CreatedAt.Format(time.RFC3339))

		if !sess.StartedAt.IsZero() {
			fmt.Printf("  Started:  %s\n", sess.StartedAt.Format(time.RFC3339))
			fmt.Printf("  Duration: %s\n", time.Since(sess.StartedAt).Truncate(time.Second))
		}

		if !sess.CompletedAt.IsZero() {
			fmt.Printf("  Completed: %s\n", sess.CompletedAt.Format(time.RFC3339))
		}

		if sess.ErrorMsg != "" {
			fmt.Printf("  Error:    %s\n", sess.ErrorMsg)
		}

		if sess.Task != "" {
			fmt.Printf("  Task:     %s\n", sess.Task)
		}

		// Show live metrics if session is running
		if snap, ok := mgr.GetMetricsSnapshot(sess.ID); ok {
			fmt.Printf("  Metrics:\n")
			fmt.Printf("    CPU:    %.1f%%\n", snap.CPUPercent)
			fmt.Printf("    Memory: %.1f MB\n", snap.MemoryMB)
			if snap.TokensUsed > 0 {
				fmt.Printf("    Tokens: %d\n", snap.TokensUsed)
			}
		}

		return nil
	},
}

func init() {
	rootCmd.AddCommand(pauseCmd)
	rootCmd.AddCommand(resumeCmd)
	rootCmd.AddCommand(killCmd)
	rootCmd.AddCommand(statusCmd)
}
