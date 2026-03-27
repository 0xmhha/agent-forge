package main

import (
	"fmt"
	"log"

	"github.com/spf13/cobra"

	"github.com/agent-forge/agent-forge/runtime/internal/daemon"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

var daemonCmd = &cobra.Command{
	Use:   "daemon",
	Short: "Manage the background daemon",
}

var daemonStartCmd = &cobra.Command{
	Use:   "start",
	Short: "Start the background daemon",
	RunE: func(cmd *cobra.Command, args []string) error {
		d := daemon.NewDaemon(cfg.Paths.DaemonPID, cfg.Paths.Log)
		if err := d.Start(); err != nil {
			return err
		}
		pid, _ := d.Status()
		fmt.Printf("Daemon started (PID %d)\n", pid)
		return nil
	},
}

var daemonStopCmd = &cobra.Command{
	Use:   "stop",
	Short: "Stop the background daemon",
	RunE: func(cmd *cobra.Command, args []string) error {
		d := daemon.NewDaemon(cfg.Paths.DaemonPID, cfg.Paths.Log)
		if err := d.Stop(); err != nil {
			return err
		}
		fmt.Println("Daemon stopped.")
		return nil
	},
}

var daemonStatusCmd = &cobra.Command{
	Use:   "status",
	Short: "Show daemon status",
	RunE: func(cmd *cobra.Command, args []string) error {
		d := daemon.NewDaemon(cfg.Paths.DaemonPID, cfg.Paths.Log)
		pid, running := d.Status()
		if running {
			fmt.Printf("Daemon is running (PID %d)\n", pid)
		} else {
			fmt.Println("Daemon is not running.")
		}
		return nil
	},
}

// daemonRunCmd is the internal command executed by the daemon process.
// Not shown in help — only called by daemon.Start().
var daemonRunCmd = &cobra.Command{
	Use:    "run",
	Hidden: true,
	RunE: func(cmd *cobra.Command, args []string) error {
		log.Printf("[daemon] initializing...")

		store := session.NewFileStore(cfg.Paths.State)
		w := daemon.NewWorker(mgr, store, cfg, evtBus)
		w.Run()

		return nil
	},
}

func init() {
	daemonCmd.AddCommand(daemonStartCmd)
	daemonCmd.AddCommand(daemonStopCmd)
	daemonCmd.AddCommand(daemonStatusCmd)
	daemonCmd.AddCommand(daemonRunCmd)

	rootCmd.AddCommand(daemonCmd)
}
