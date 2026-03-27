package monitor

import (
	"regexp"
	"strconv"
	"strings"
)

// TokenCollector parses token usage from Claude Code stdout.
type TokenCollector struct{}

func (c *TokenCollector) Name() string { return "token" }

func (c *TokenCollector) Collect(_ int, output string) (CollectorResult, error) {
	tokens := parseTokenUsage(output)
	return CollectorResult{
		TokensUsed: tokens,
	}, nil
}

// Token usage patterns in Claude Code output:
//   "Total tokens: 12,345"
//   "tokens: 12345"
//   "Token usage: 12,345 / 50,000"
//   "Cost: $0.12 (1,234 tokens)"
var tokenPatterns = []*regexp.Regexp{
	regexp.MustCompile(`(?i)total\s+tokens?[:\s]+([0-9,]+)`),
	regexp.MustCompile(`(?i)token\s+usage[:\s]+([0-9,]+)`),
	regexp.MustCompile(`(?i)\(([0-9,]+)\s+tokens?\)`),
	regexp.MustCompile(`(?i)tokens?[:\s]+([0-9,]+)`),
}

// parseTokenUsage extracts the highest token count from output text.
func parseTokenUsage(output string) int64 {
	var maxTokens int64

	for _, pattern := range tokenPatterns {
		matches := pattern.FindAllStringSubmatch(output, -1)
		for _, match := range matches {
			if len(match) < 2 {
				continue
			}
			cleaned := strings.ReplaceAll(match[1], ",", "")
			n, err := strconv.ParseInt(cleaned, 10, 64)
			if err != nil {
				continue
			}
			if n > maxTokens {
				maxTokens = n
			}
		}
	}

	return maxTokens
}
