"""Tests for shared.sanitize — token pattern redaction.

sanitize() is the last defense against token leakage in MCP tool results.
Every token pattern must be independently verified.
"""

import pytest

from shared.sanitize import sanitize


class TestSanitizeIndividualPatterns:
    """Each token pattern should be independently redacted."""

    @pytest.mark.parametrize(
        "token, description",
        [
            ("ya29.a0ARrdaM_fake_google_token_value", "Google OAuth access token"),
            ("ghp_1234567890abcdefABCDEF", "GitHub PAT classic"),
            ("gho_abcdef1234567890ABCDEF", "GitHub OAuth token"),
            ("github_pat_11AAAAAA_abcdef1234567890", "GitHub fine-grained PAT"),
            ("ghs_abcdef1234567890", "GitHub server-to-server (App)"),
            ("ghr_abcdef1234567890", "GitHub refresh token"),
            ("gha_abcdef1234567890", "GitHub Actions token"),
        ],
    )
    def test_prefix_token_redacted(self, token: str, description: str):
        text = f"Error: authentication failed with {token} for service"
        result = sanitize(text)

        assert token not in result
        assert "[REDACTED]" in result
        assert "Error: authentication failed with" in result

    def test_bearer_header_redacted(self):
        text = "Authorization: Bearer eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.payload.sig"
        result = sanitize(text)

        assert "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9" not in result
        assert "[REDACTED]" in result

    def test_generic_token_header_redacted(self):
        text = "Authorization: token ghp_1234567890abcdef"
        result = sanitize(text)

        assert "ghp_1234567890abcdef" not in result
        assert "[REDACTED]" in result

    def test_bearer_case_insensitive(self):
        text = "header: BEARER my_secret_jwt_value"
        result = sanitize(text)

        assert "my_secret_jwt_value" not in result
        assert "[REDACTED]" in result

    def test_token_case_insensitive(self):
        text = "header: TOKEN some_secret_value"
        result = sanitize(text)

        assert "some_secret_value" not in result
        assert "[REDACTED]" in result


class TestSanitizePassthrough:
    """Normal text without tokens should pass through unchanged."""

    def test_plain_text_unchanged(self):
        text = "This is a normal error message with no tokens"
        assert sanitize(text) == text

    def test_empty_string(self):
        assert sanitize("") == ""

    def test_text_with_similar_but_non_matching_prefixes(self):
        text = "ghp without underscore is not a token"
        assert sanitize(text) == text

    def test_url_without_token(self):
        text = "https://api.github.com/repos/owner/repo/issues"
        assert sanitize(text) == text


class TestSanitizeMultipleTokens:
    """Multiple tokens in one string should all be redacted."""

    def test_two_different_tokens(self):
        text = "gmail=ya29.fake_token github=ghp_abcdef123456"
        result = sanitize(text)

        assert "ya29." not in result
        assert "ghp_" not in result
        assert result.count("[REDACTED]") == 2

    def test_same_type_repeated(self):
        text = "first=ghp_aaaa1111 second=ghp_bbbb2222"
        result = sanitize(text)

        assert "ghp_aaaa1111" not in result
        assert "ghp_bbbb2222" not in result
        assert result.count("[REDACTED]") == 2

    def test_tokens_across_lines(self):
        text = (
            "Error on line 1: Bearer secret_jwt_value\n"
            "Error on line 2: token ghp_abcdef123456\n"
            "Normal line 3: no tokens here"
        )
        result = sanitize(text)

        assert "secret_jwt_value" not in result
        assert "ghp_abcdef123456" not in result
        assert "Normal line 3: no tokens here" in result


class TestSanitizeEdgeCases:
    """Edge cases and boundary conditions."""

    def test_token_only_string(self):
        result = sanitize("ghp_abcdef1234567890")
        assert result == "[REDACTED]"

    def test_token_at_start(self):
        result = sanitize("ya29.fake_token caused the error")
        assert result.startswith("[REDACTED]")
        assert "caused the error" in result

    def test_token_at_end(self):
        result = sanitize("Failed with token ghp_abcdef1234")
        assert result.endswith("[REDACTED]")

    def test_minimal_length_tokens(self):
        """Shortest possible tokens should still match."""
        assert "ghp_a" not in sanitize("x ghp_a y")
        assert "gho_a" not in sanitize("x gho_a y")
        assert "ghs_a" not in sanitize("x ghs_a y")

    def test_long_google_token(self):
        long_token = "ya29." + "A" * 200
        result = sanitize(f"token: {long_token}")
        assert long_token not in result

    def test_embedded_in_json(self):
        text = '{"error": "auth failed", "token": "Bearer eyJhbG.payload.sig"}'
        result = sanitize(text)
        assert "eyJhbG" not in result
