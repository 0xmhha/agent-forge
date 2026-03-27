package main

import (
	"fmt"
	"os"
	"text/tabwriter"

	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

var listFlags struct {
	status string
}

var listCmd = &cobra.Command{
	Use:     "list",
	Short:   "List all sessions",
	Aliases: []string{"ls"},
	RunE:    runList,
}

func init() {
	listCmd.Flags().StringVar(&listFlags.status, "status", "", "filter by status")

	rootCmd.AddCommand(listCmd)
}

func runList(cmd *cobra.Command, args []string) error {
	sessions := mgr.List()

	if len(sessions) == 0 {
		fmt.Println("No sessions found.")
		return nil
	}

	// Filter by status if specified
	if listFlags.status != "" {
		var filtered []*session.Session
		for _, s := range sessions {
			if s.Status.String() == listFlags.status {
				filtered = append(filtered, s)
			}
		}
		sessions = filtered
	}

	w := tabwriter.NewWriter(os.Stdout, 0, 0, 2, ' ', 0)
	fmt.Fprintln(w, "ID\tTITLE\tSTATUS\tPOLICY\tCREATED")
	for _, s := range sessions {
		shortID := s.ID
		if len(shortID) > 8 {
			shortID = shortID[:8]
		}
		fmt.Fprintf(w, "%s\t%s\t%s\t%s\t%s\n",
			shortID,
			s.Title,
			statusIcon(s.Status)+" "+s.Status.String(),
			s.PolicyName,
			s.CreatedAt.Format("2006-01-02 15:04"),
		)
	}
	return w.Flush()
}
