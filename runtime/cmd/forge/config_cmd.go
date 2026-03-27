package main

import (
	"encoding/json"
	"fmt"

	"github.com/spf13/cobra"
)

var configCmd = &cobra.Command{
	Use:   "config",
	Short: "Show current configuration",
	RunE: func(cmd *cobra.Command, args []string) error {
		data, err := json.MarshalIndent(cfg, "", "  ")
		if err != nil {
			return fmt.Errorf("failed to marshal config: %w", err)
		}

		fmt.Println(string(data))
		fmt.Printf("\nConfig file: %s\n", cfg.Paths.Config)
		fmt.Printf("State file:  %s\n", cfg.Paths.State)
		fmt.Printf("Sessions:    %s\n", cfg.Paths.SessionsDir)

		return nil
	},
}

func init() {
	rootCmd.AddCommand(configCmd)
}
