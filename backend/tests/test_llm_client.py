"""Unit tests for the FallbackLLMClient and provider classes."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.llm.client import (
    FallbackLLMClient,
    OpenRouterProvider,
    OPENROUTER_DEFAULT_MODEL,
    _parse_json,
)
from app.llm.exceptions import LLMError, LLMParseError, LLMUnavailableError


# ── _parse_json ────────────────────────────────────────────────────────────────

def test_parse_json_plain():
    assert _parse_json('{"key": "value"}') == {"key": "value"}


def test_parse_json_markdown_fence():
    text = '```json\n{"key": "value"}\n```'
    assert _parse_json(text) == {"key": "value"}


def test_parse_json_markdown_fence_no_lang():
    text = '```\n{"key": "value"}\n```'
    assert _parse_json(text) == {"key": "value"}


def test_parse_json_embedded():
    text = 'Some preamble {"key": "value"} trailing text'
    assert _parse_json(text) == {"key": "value"}


def test_parse_json_invalid_raises():
    with pytest.raises(LLMParseError):
        _parse_json("this is not json at all")


# ── FallbackLLMClient ──────────────────────────────────────────────────────────

class _MockProvider:
    """Stub provider for testing the fallback chain."""

    def __init__(self, name: str, response=None, raises=None):
        self.name = name
        self._response = response
        self._raises = raises
        self.calls = 0

    async def complete_text(self, system, user, **kwargs):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._response

    async def complete_json(self, system, user, **kwargs):
        self.calls += 1
        if self._raises:
            raise self._raises
        return self._response


@pytest.mark.asyncio
async def test_fallback_uses_first_provider():
    p1 = _MockProvider("p1", response="hello")
    p2 = _MockProvider("p2", response="world")
    client = FallbackLLMClient([p1, p2])

    result = await client.complete_text("sys", "user")
    assert result == "hello"
    assert p1.calls == 1
    assert p2.calls == 0


@pytest.mark.asyncio
async def test_fallback_skips_unavailable_provider():
    p1 = _MockProvider("p1", raises=LLMUnavailableError("down"))
    p2 = _MockProvider("p2", response="from p2")
    client = FallbackLLMClient([p1, p2])

    result = await client.complete_text("sys", "user")
    assert result == "from p2"
    assert p1.calls == 1
    assert p2.calls == 1


@pytest.mark.asyncio
async def test_fallback_skips_on_llm_error():
    p1 = _MockProvider("p1", raises=LLMError("bad response"))
    p2 = _MockProvider("p2", response="ok")
    client = FallbackLLMClient([p1, p2])

    result = await client.complete_text("sys", "user")
    assert result == "ok"


@pytest.mark.asyncio
async def test_fallback_raises_when_all_exhausted():
    p1 = _MockProvider("p1", raises=LLMUnavailableError("p1 down"))
    p2 = _MockProvider("p2", raises=LLMUnavailableError("p2 down"))
    client = FallbackLLMClient([p1, p2])

    with pytest.raises(LLMUnavailableError, match="All LLM providers exhausted"):
        await client.complete_text("sys", "user")


def test_fallback_requires_at_least_one_provider():
    with pytest.raises(ValueError, match="at least one provider"):
        FallbackLLMClient([])


# ── OpenRouterProvider ─────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_openrouter_provider_uses_correct_base_url():
    """OpenRouterProvider should configure AsyncOpenAI with OpenRouter's base_url."""
    with patch("openai.AsyncOpenAI") as mock_cls:
        mock_client = MagicMock()
        mock_cls.return_value = mock_client

        provider = OpenRouterProvider(api_key="sk-or-test")

        mock_cls.assert_called_once_with(
            api_key="sk-or-test",
            base_url="https://openrouter.ai/api/v1",
        )
        assert provider.model == OPENROUTER_DEFAULT_MODEL
        assert provider.name == "openrouter"


@pytest.mark.asyncio
async def test_openrouter_complete_text():
    """OpenRouterProvider.complete_text should return the LLM response text."""
    with patch("openai.AsyncOpenAI") as mock_cls:
        mock_choice = MagicMock()
        mock_choice.message.content = "OpenRouter says hello"
        mock_response = MagicMock()
        mock_response.choices = [mock_choice]

        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(return_value=mock_response)
        mock_cls.return_value = mock_async_client

        provider = OpenRouterProvider(api_key="sk-or-test")
        result = await provider.complete_text("You are helpful.", "Say hello.")
        assert result == "OpenRouter says hello"


@pytest.mark.asyncio
async def test_openrouter_auth_error_raises_unavailable():
    """AuthenticationError from OpenRouter should become LLMUnavailableError."""
    import openai

    with patch("openai.AsyncOpenAI") as mock_cls:
        mock_async_client = MagicMock()
        mock_async_client.chat.completions.create = AsyncMock(
            side_effect=openai.AuthenticationError(
                "Invalid key",
                response=MagicMock(status_code=401),
                body={"error": {"message": "Invalid API key"}},
            )
        )
        mock_cls.return_value = mock_async_client

        provider = OpenRouterProvider(api_key="bad-key")

        with pytest.raises(LLMUnavailableError, match="OpenRouter"):
            await provider.complete_text("sys", "user")


@pytest.mark.asyncio
async def test_openrouter_is_last_in_fallback_chain():
    """OpenRouterProvider should sit last in the get_llm_client chain."""
    from app.llm.client import get_llm_client, _client as existing_client
    import app.llm.client as llm_module

    # Reset the singleton so get_llm_client re-builds it
    original = llm_module._client
    llm_module._client = None

    try:
        mock_settings = MagicMock()
        mock_settings.openai_api_key = "sk-openai"
        mock_settings.anthropic_api_key = ""
        mock_settings.gemini_api_key = ""
        mock_settings.groq_api_key = ""
        mock_settings.openrouter_api_key = "sk-or-test"

        with patch("app.llm.client.get_settings", return_value=mock_settings), \
             patch("openai.AsyncOpenAI"):
            client = get_llm_client()
            names = [p.name for p in client._providers]
            assert names[0] == "openai"
            assert names[-1] == "openrouter"
    finally:
        llm_module._client = original
