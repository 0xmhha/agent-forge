package main

import (
	"fmt"

	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

var newFlags struct {
	task     string
	project  string
	policy   string
	worktree bool
	budget   int64
}

var newCmd = &cobra.Command{
	Use:   "new <title>",
	Short: "Create a new session",
	Args:  cobra.ExactArgs(1),
	RunE:  runNew,
}

func init() {
	newCmd.Flags().StringVar(&newFlags.task, "task", "", "task description for the AI")
	newCmd.Flags().StringVar(&newFlags.project, "project", "", "target project path")
	newCmd.Flags().StringVar(&newFlags.policy, "policy", "", "security policy (readonly/restricted/standard/full)")
	newCmd.Flags().BoolVar(&newFlags.worktree, "worktree", false, "use git worktree")
	newCmd.Flags().Int64Var(&newFlags.budget, "budget", 0, "token budget (0 = unlimited)")

	rootCmd.AddCommand(newCmd)
}

func runNew(cmd *cobra.Command, args []string) error {
	sess, err := mgr.Create(session.SessionConfig{
		Title:       args[0],
		Task:        newFlags.task,
		ProjectPath: newFlags.project,
		PolicyName:  newFlags.policy,
		UseWorktree: newFlags.worktree,
		TokenBudget: newFlags.budget,
	})
	if err != nil {
		return err
	}

	fmt.Printf("Session created: %s\n", sess.ID)
	fmt.Printf("  Title:   %s\n", sess.Title)
	fmt.Printf("  Policy:  %s\n", sess.PolicyName)
	fmt.Printf("  Sandbox: %s\n", sess.SandboxDir)

	return nil
}
