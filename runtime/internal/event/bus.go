package event

import (
	"sync"
	"time"
)

// Type represents the kind of event.
type Type int

const (
	SessionCreated       Type = iota
	SessionStarted
	SessionStatusChanged
	SessionOutputChanged
	SessionCompleted
	SessionFailed
	MetricsUpdated
)

func (t Type) String() string {
	switch t {
	case SessionCreated:
		return "session.created"
	case SessionStarted:
		return "session.started"
	case SessionStatusChanged:
		return "session.status_changed"
	case SessionOutputChanged:
		return "session.output_changed"
	case SessionCompleted:
		return "session.completed"
	case SessionFailed:
		return "session.failed"
	case MetricsUpdated:
		return "metrics.updated"
	default:
		return "unknown"
	}
}

// Event represents a system event.
type Event struct {
	Type      Type
	SessionID string
	Data      any
	Timestamp time.Time
}

// Bus defines the event pub/sub interface.
type Bus interface {
	Publish(event Event)
	Subscribe(types ...Type) <-chan Event
	Unsubscribe(ch <-chan Event)
	Close()
}

// ChannelBus is a channel-based Bus implementation.
type ChannelBus struct {
	subscribers map[Type][]chan Event
	mu          sync.RWMutex
	closed      bool
	bufferSize  int
}

// NewChannelBus creates a new channel-based event bus.
func NewChannelBus(bufferSize int) *ChannelBus {
	return &ChannelBus{
		subscribers: make(map[Type][]chan Event),
		bufferSize:  bufferSize,
	}
}

// Publish sends an event to all subscribers of that event type.
func (b *ChannelBus) Publish(evt Event) {
	b.mu.RLock()
	defer b.mu.RUnlock()

	if b.closed {
		return
	}

	if evt.Timestamp.IsZero() {
		evt.Timestamp = time.Now()
	}

	for _, ch := range b.subscribers[evt.Type] {
		select {
		case ch <- evt:
		default:
			// Drop event if subscriber buffer is full
		}
	}
}

// Subscribe returns a channel that receives events of the specified types.
func (b *ChannelBus) Subscribe(types ...Type) <-chan Event {
	b.mu.Lock()
	defer b.mu.Unlock()

	ch := make(chan Event, b.bufferSize)
	for _, t := range types {
		b.subscribers[t] = append(b.subscribers[t], ch)
	}
	return ch
}

// Unsubscribe removes a channel from all event types.
func (b *ChannelBus) Unsubscribe(ch <-chan Event) {
	b.mu.Lock()
	defer b.mu.Unlock()

	for t, subs := range b.subscribers {
		filtered := make([]chan Event, 0, len(subs))
		for _, s := range subs {
			if (<-chan Event)(s) != ch {
				filtered = append(filtered, s)
			}
		}
		b.subscribers[t] = filtered
	}
}

// Close shuts down the event bus and closes all subscriber channels.
func (b *ChannelBus) Close() {
	b.mu.Lock()
	defer b.mu.Unlock()

	if b.closed {
		return
	}
	b.closed = true

	closed := make(map[chan Event]bool)
	for _, subs := range b.subscribers {
		for _, ch := range subs {
			if !closed[ch] {
				close(ch)
				closed[ch] = true
			}
		}
	}
}
