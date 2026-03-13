"""LLM-specific exceptions."""


class LLMError(Exception):
    """Base exception for LLM operations."""


class LLMParseError(LLMError):
    """Failed to parse LLM response as expected format."""


class LLMUnavailableError(LLMError):
    """LLM service unreachable or API key invalid."""
