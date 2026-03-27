package session

import (
	"encoding/json"
	"errors"
	"os"
	"sync"
)

// Store defines the persistence interface for sessions.
type Store interface {
	SaveAll(sessions []*Session) error
	LoadAll() ([]*Session, error)
	Save(session *Session) error
	Delete(sessionID string) error
}

// stateFile represents the serialized state file format.
type stateFile struct {
	Version  string     `json:"version"`
	Sessions []*Session `json:"sessions"`
}

// FileStore is a JSON file-based Store implementation.
type FileStore struct {
	path string
	mu   sync.Mutex
}

// NewFileStore creates a new FileStore at the given path.
func NewFileStore(path string) *FileStore {
	return &FileStore{path: path}
}

// SaveAll writes all sessions to the state file.
func (fs *FileStore) SaveAll(sessions []*Session) error {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	state := stateFile{
		Version:  "1.0",
		Sessions: sessions,
	}

	return fs.writeState(state)
}

// LoadAll reads all sessions from the state file.
func (fs *FileStore) LoadAll() ([]*Session, error) {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	state, err := fs.readState()
	if err != nil {
		return nil, err
	}

	return state.Sessions, nil
}

// Save persists a single session (upsert into the state file).
func (fs *FileStore) Save(session *Session) error {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	state, err := fs.readState()
	if err != nil {
		return err
	}

	found := false
	for i, s := range state.Sessions {
		if s.ID == session.ID {
			state.Sessions[i] = session
			found = true
			break
		}
	}

	if !found {
		state.Sessions = append(state.Sessions, session)
	}

	return fs.writeState(state)
}

// Delete removes a session from the state file.
func (fs *FileStore) Delete(sessionID string) error {
	fs.mu.Lock()
	defer fs.mu.Unlock()

	state, err := fs.readState()
	if err != nil {
		return err
	}

	filtered := make([]*Session, 0, len(state.Sessions))
	for _, s := range state.Sessions {
		if s.ID != sessionID {
			filtered = append(filtered, s)
		}
	}

	state.Sessions = filtered
	return fs.writeState(state)
}

func (fs *FileStore) readState() (stateFile, error) {
	data, err := os.ReadFile(fs.path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return stateFile{Version: "1.0", Sessions: []*Session{}}, nil
		}
		return stateFile{}, err
	}

	var state stateFile
	if err := json.Unmarshal(data, &state); err != nil {
		return stateFile{}, err
	}

	if state.Sessions == nil {
		state.Sessions = []*Session{}
	}

	return state, nil
}

func (fs *FileStore) writeState(state stateFile) error {
	data, err := json.MarshalIndent(state, "", "  ")
	if err != nil {
		return err
	}

	return os.WriteFile(fs.path, data, 0640)
}
