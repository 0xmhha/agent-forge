package daemon

import (
	"log"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/agent-forge/agent-forge/runtime/internal/config"
	"github.com/agent-forge/agent-forge/runtime/internal/event"
	"github.com/agent-forge/agent-forge/runtime/internal/session"
)

// Worker runs background tasks: session monitoring, auto-save.
type Worker struct {
	manager    *session.SessionManager
	store      session.Store
	config     *config.Config
	bus        event.Bus
	saveInterval time.Duration
}

// NewWorker creates a new background worker.
func NewWorker(mgr *session.SessionManager, store session.Store, cfg *config.Config, bus event.Bus) *Worker {
	return &Worker{
		manager:      mgr,
		store:        store,
		config:       cfg,
		bus:          bus,
		saveInterval: 30 * time.Second,
	}
}

// Run starts the worker loop. Blocks until SIGTERM/SIGINT.
func (w *Worker) Run() {
	log.Println("[daemon] worker started")

	// Start session monitoring loops
	w.manager.StartLoops()
	defer w.manager.StopLoops()

	// Signal handling
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGTERM, syscall.SIGINT)

	// Periodic auto-save
	saveTicker := time.NewTicker(w.saveInterval)
	defer saveTicker.Stop()

	for {
		select {
		case sig := <-sigCh:
			log.Printf("[daemon] received signal: %v, shutting down", sig)
			w.save()
			return

		case <-saveTicker.C:
			w.save()
		}
	}
}

func (w *Worker) save() {
	sessions := w.manager.List()
	if err := w.store.SaveAll(sessions); err != nil {
		log.Printf("[daemon] auto-save failed: %v", err)
	} else {
		log.Printf("[daemon] auto-saved %d sessions", len(sessions))
	}
}
