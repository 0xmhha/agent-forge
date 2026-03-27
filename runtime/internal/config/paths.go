package config

import (
	"os"
	"path/filepath"
)

const (
	appDirName     = ".forge"
	configFileName = "config.json"
	stateFileName  = "state.json"
	logFileName    = "forge.log"
	daemonPIDFile  = "daemon.pid"
	sessionsDirName = "sessions"
)

// Paths holds resolved filesystem paths for the application.
type Paths struct {
	Root       string // ~/.forge
	Config     string // ~/.forge/config.json
	State      string // ~/.forge/state.json
	Log        string // ~/.forge/forge.log
	DaemonPID  string // ~/.forge/daemon.pid
	SessionsDir string // ~/.forge/sessions
}

// ResolvePaths returns application paths based on the user's home directory.
// Respects FORGE_HOME environment variable if set.
func ResolvePaths() (Paths, error) {
	root, err := resolveRoot()
	if err != nil {
		return Paths{}, err
	}

	return Paths{
		Root:        root,
		Config:      filepath.Join(root, configFileName),
		State:       filepath.Join(root, stateFileName),
		Log:         filepath.Join(root, logFileName),
		DaemonPID:   filepath.Join(root, daemonPIDFile),
		SessionsDir: filepath.Join(root, sessionsDirName),
	}, nil
}

// SessionDir returns the sandbox directory path for a given session ID.
func (p Paths) SessionDir(sessionID string) string {
	return filepath.Join(p.SessionsDir, sessionID)
}

// EnsureDirs creates all required directories if they don't exist.
func (p Paths) EnsureDirs() error {
	dirs := []string{p.Root, p.SessionsDir}
	for _, dir := range dirs {
		if err := os.MkdirAll(dir, 0750); err != nil {
			return err
		}
	}
	return nil
}

func resolveRoot() (string, error) {
	if envRoot := os.Getenv("FORGE_HOME"); envRoot != "" {
		return envRoot, nil
	}

	home, err := os.UserHomeDir()
	if err != nil {
		return "", err
	}

	return filepath.Join(home, appDirName), nil
}
