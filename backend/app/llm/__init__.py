"""LLM integration module for KEEN agents.

Provides a multi-provider client with automatic Claude → Gemini failover.
"""

from app.llm.client import (
    BaseLLMProvider,
    ClaudeProvider,
    FallbackLLMClient,
    GeminiProvider,
    LLMClient,
    get_llm_client,
)
from app.llm.exceptions import LLMError, LLMParseError, LLMUnavailableError

__all__ = [
    # Client
    "FallbackLLMClient",
    "LLMClient",           # backward-compatible alias
    "get_llm_client",
    # Providers
    "BaseLLMProvider",
    "ClaudeProvider",
    "GeminiProvider",
    # Exceptions
    "LLMError",
    "LLMParseError",
    "LLMUnavailableError",
]
