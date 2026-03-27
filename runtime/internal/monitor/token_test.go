package monitor

import "testing"

func TestParseTokenUsage(t *testing.T) {
	tests := []struct {
		name     string
		output   string
		expected int64
	}{
		{
			name:     "total tokens with comma",
			output:   "Total tokens: 12,345",
			expected: 12345,
		},
		{
			name:     "token usage fraction",
			output:   "Token usage: 23,450 / 50,000",
			expected: 23450,
		},
		{
			name:     "parenthesized tokens",
			output:   "Cost: $0.12 (1,234 tokens)",
			expected: 1234,
		},
		{
			name:     "simple tokens",
			output:   "tokens: 9999",
			expected: 9999,
		},
		{
			name:     "no tokens in output",
			output:   "Hello world, no token info here",
			expected: 0,
		},
		{
			name:     "multiple patterns pick highest",
			output:   "tokens: 100\nTotal tokens: 5,000\n(200 tokens)",
			expected: 5000,
		},
		{
			name:     "empty output",
			output:   "",
			expected: 0,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			result := parseTokenUsage(tc.output)
			if result != tc.expected {
				t.Errorf("expected %d, got %d", tc.expected, result)
			}
		})
	}
}
