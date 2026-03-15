"""Multi-provider async LLM client with automatic OpenAI → Claude → Gemini failover.

Priority order: OpenAI (GPT-4o) → Claude (Anthropic) → Gemini (Google).
On LLMUnavailableError (auth failure, rate-limit, quota exhausted, service
down), the next configured provider is tried automatically.  At least one
API key must be present in settings.
"""

from __future__ import annotations

import abc
import json
import logging
import re
import time
from typing import Sequence

from app.config import get_settings
from app.llm.exceptions import LLMError, LLMParseError, LLMUnavailableError

logger = logging.getLogger(__name__)

OPENAI_DEFAULT_MODEL  = "gpt-4o"
CLAUDE_DEFAULT_MODEL  = "claude-sonnet-4-20250514"
GEMINI_DEFAULT_MODEL  = "gemini-2.0-flash"
GROQ_DEFAULT_MODEL    = "llama-3.3-70b-versatile"


# ── Shared JSON parser ─────────────────────────────────────────────────────────

def _parse_json(text: str) -> dict:
    """Extract and parse JSON from LLM response text, stripping markdown fences."""
    cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
    cleaned = re.sub(r"\n?```\s*$", "", cleaned)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as exc:
        match = re.search(r"\{[\s\S]*\}", cleaned)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
        raise LLMParseError(f"Could not parse JSON from response: {exc}") from exc


# ── Abstract provider interface ────────────────────────────────────────────────

class BaseLLMProvider(abc.ABC):
    """Common interface that every LLM provider must implement."""

    name: str = "base"

    @abc.abstractmethod
    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        """Send a prompt and return a parsed JSON dict."""
        ...

    @abc.abstractmethod
    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        """Send a prompt and return the plain-text response."""
        ...


# ── OpenAI provider ───────────────────────────────────────────────────────────

class OpenAIProvider(BaseLLMProvider):
    """OpenAI GPT-4o via the openai async SDK."""

    name = "openai"

    def __init__(self, api_key: str, model: str = OPENAI_DEFAULT_MODEL) -> None:
        import openai as _openai  # lazy import
        self._openai = _openai
        self._client = _openai.AsyncOpenAI(api_key=api_key)
        self.model = model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        raw = await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)
        try:
            return _parse_json(raw)
        except LLMParseError:
            logger.warning("[OpenAI] JSON parse failed — retrying with explicit instruction")
            raw = await self._send(
                system_prompt,
                (
                    "Your previous response was not valid JSON. "
                    "Respond ONLY with valid JSON — no markdown, no commentary.\n\n"
                    + user_prompt
                ),
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return _parse_json(raw)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        return await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)

    async def _send(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content or ""
            logger.info(
                "[OpenAI] model=%s prompt_len=%d response_len=%d latency=%.1fs",
                self.model, len(user_prompt), len(text), time.monotonic() - start,
            )
            return text

        except self._openai.AuthenticationError as exc:
            raise LLMUnavailableError(f"[OpenAI] Invalid API key: {exc}") from exc
        except self._openai.RateLimitError as exc:
            raise LLMUnavailableError(f"[OpenAI] Rate limit / quota exceeded: {exc}") from exc
        except self._openai.APIStatusError as exc:
            if exc.status_code in (429, 529):
                raise LLMUnavailableError(f"[OpenAI] Overloaded ({exc.status_code}): {exc}") from exc
            raise LLMError(f"[OpenAI] API error {exc.status_code}: {exc}") from exc
        except self._openai.APIError as exc:
            raise LLMError(f"[OpenAI] API error: {exc}") from exc


# ── Claude (Anthropic) provider ────────────────────────────────────────────────

class ClaudeProvider(BaseLLMProvider):
    """Anthropic Claude via the anthropic async SDK."""

    name = "claude"

    def __init__(self, api_key: str, model: str = CLAUDE_DEFAULT_MODEL) -> None:
        import anthropic as _anthropic  # lazy import — only needed if key is set
        self._anthropic = _anthropic
        self._client = _anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        raw = await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)
        try:
            return _parse_json(raw)
        except LLMParseError:
            logger.warning("[Claude] JSON parse failed — retrying with explicit instruction")
            raw = await self._send(
                system_prompt,
                (
                    "Your previous response was not valid JSON. "
                    "Respond ONLY with valid JSON — no markdown, no commentary.\n\n"
                    + user_prompt
                ),
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return _parse_json(raw)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        return await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)

    async def _send(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        import asyncio

        start = time.monotonic()
        try:
            response = await self._client.messages.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            logger.info(
                "[Claude] model=%s prompt_len=%d response_len=%d latency=%.1fs",
                self.model, len(user_prompt), len(text), time.monotonic() - start,
            )
            return text

        except self._anthropic.AuthenticationError as exc:
            raise LLMUnavailableError(f"[Claude] Invalid API key: {exc}") from exc

        except self._anthropic.RateLimitError as exc:
            # Surface as unavailable so the fallback chain tries Gemini
            raise LLMUnavailableError(f"[Claude] Rate limit / quota exceeded: {exc}") from exc

        except self._anthropic.APIStatusError as exc:
            if exc.status_code in (429, 529):
                raise LLMUnavailableError(f"[Claude] Overloaded ({exc.status_code}): {exc}") from exc
            raise LLMError(f"[Claude] API error {exc.status_code}: {exc}") from exc

        except self._anthropic.APIError as exc:
            raise LLMError(f"[Claude] API error: {exc}") from exc


# ── Gemini (Google) provider ───────────────────────────────────────────────────

class GeminiProvider(BaseLLMProvider):
    """Google Gemini via the google-generativeai SDK (sync SDK run in thread pool)."""

    name = "gemini"

    def __init__(self, api_key: str, model: str = GEMINI_DEFAULT_MODEL) -> None:
        import google.generativeai as genai  # lazy import
        genai.configure(api_key=api_key)
        self._genai = genai
        self.model = model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        raw = await self._send(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=True,
        )
        try:
            return _parse_json(raw)
        except LLMParseError:
            logger.warning("[Gemini] JSON parse failed — retrying with explicit instruction")
            raw = await self._send(
                system_prompt,
                (
                    "Your previous response was not valid JSON. "
                    "Respond ONLY with valid JSON — no markdown, no commentary.\n\n"
                    + user_prompt
                ),
                max_tokens=max_tokens,
                temperature=0.1,
                json_mode=True,
            )
            return _parse_json(raw)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        return await self._send(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            json_mode=False,
        )

    async def _send(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        json_mode: bool,
    ) -> str:
        import asyncio

        gen_config: dict = {"max_output_tokens": max_tokens, "temperature": temperature}
        if json_mode:
            gen_config["response_mime_type"] = "application/json"

        model = self._genai.GenerativeModel(
            model_name=self.model,
            system_instruction=system_prompt,
            generation_config=gen_config,
        )

        start = time.monotonic()
        try:
            # google-generativeai SDK is synchronous — run in thread pool
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: model.generate_content(user_prompt)
            )
            text = response.text
            logger.info(
                "[Gemini] model=%s prompt_len=%d response_len=%d latency=%.1fs",
                self.model, len(user_prompt), len(text), time.monotonic() - start,
            )
            return text

        except Exception as exc:
            self._handle_error(exc)

    def _handle_error(self, exc: Exception) -> None:
        """Translate google-api-core exceptions into LLMError hierarchy."""
        try:
            import google.api_core.exceptions as gexc

            if isinstance(exc, (gexc.Unauthenticated, gexc.PermissionDenied)):
                raise LLMUnavailableError(f"[Gemini] Auth error: {exc}") from exc
            if isinstance(exc, gexc.ResourceExhausted):
                raise LLMUnavailableError(f"[Gemini] Quota exceeded: {exc}") from exc
            if isinstance(exc, gexc.ServiceUnavailable):
                raise LLMUnavailableError(f"[Gemini] Service unavailable: {exc}") from exc
            if isinstance(exc, gexc.DeadlineExceeded):
                raise LLMUnavailableError(f"[Gemini] Deadline exceeded: {exc}") from exc
        except ImportError:
            pass  # google.api_core not installed, fall through to generic

        # Catch quota / auth signals that surface as plain exceptions in some SDK versions
        err_lower = str(exc).lower()
        if any(kw in err_lower for kw in ("quota", "rate limit", "resource exhausted")):
            raise LLMUnavailableError(f"[Gemini] Quota/rate limit: {exc}") from exc
        if any(kw in err_lower for kw in ("api key", "authentication", "permission denied", "unauthenticated")):
            raise LLMUnavailableError(f"[Gemini] Auth error: {exc}") from exc

        raise LLMError(f"[Gemini] API error: {exc}") from exc


# ── Groq provider ─────────────────────────────────────────────────────────────

class GroqProvider(BaseLLMProvider):
    """Groq LPU inference via the groq async SDK."""

    name = "groq"

    def __init__(self, api_key: str, model: str = GROQ_DEFAULT_MODEL) -> None:
        from groq import AsyncGroq  # lazy import
        self._client = AsyncGroq(api_key=api_key)
        self.model = model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        raw = await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)
        try:
            return _parse_json(raw)
        except LLMParseError:
            logger.warning("[Groq] JSON parse failed — retrying with explicit instruction")
            raw = await self._send(
                system_prompt,
                (
                    "Your previous response was not valid JSON. "
                    "Respond ONLY with valid JSON — no markdown, no commentary.\n\n"
                    + user_prompt
                ),
                max_tokens=max_tokens,
                temperature=0.1,
            )
            return _parse_json(raw)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        return await self._send(system_prompt, user_prompt, max_tokens=max_tokens, temperature=temperature)

    async def _send(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
    ) -> str:
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user",   "content": user_prompt},
                ],
            )
            text = response.choices[0].message.content or ""
            logger.info(
                "[Groq] model=%s prompt_len=%d response_len=%d latency=%.1fs",
                self.model, len(user_prompt), len(text), time.monotonic() - start,
            )
            return text
        except Exception as exc:
            exc_str = str(exc)
            if "invalid_api_key" in exc_str.lower() or "401" in exc_str:
                raise LLMUnavailableError(f"[Groq] Invalid API key: {exc}") from exc
            if "429" in exc_str or "rate" in exc_str.lower() or "quota" in exc_str.lower():
                raise LLMUnavailableError(f"[Groq] Rate limited / quota exceeded: {exc}") from exc
            raise LLMError(f"[Groq] API error: {exc}") from exc


# ── Fallback client ────────────────────────────────────────────────────────────

class FallbackLLMClient:
    """Tries providers in order; automatically falls back on LLMUnavailableError.

    Usage::

        client = FallbackLLMClient([ClaudeProvider(...), GeminiProvider(...)])
        result = await client.complete_json(system, user)
    """

    def __init__(self, providers: Sequence[BaseLLMProvider]) -> None:
        if not providers:
            raise ValueError("FallbackLLMClient requires at least one provider")
        self._providers = list(providers)
        logger.info(
            "[LLM] Fallback chain: %s",
            " → ".join(p.name for p in self._providers),
        )

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
    ) -> dict:
        return await self._with_fallback(
            "complete_json", system_prompt, user_prompt,
            max_tokens=max_tokens, temperature=temperature,
        )

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
    ) -> str:
        return await self._with_fallback(
            "complete_text", system_prompt, user_prompt,
            max_tokens=max_tokens, temperature=temperature,
        )

    async def _with_fallback(self, method: str, system_prompt: str, user_prompt: str, **kwargs):
        last_error: Exception | None = None
        for provider in self._providers:
            try:
                return await getattr(provider, method)(system_prompt, user_prompt, **kwargs)
            except LLMUnavailableError as exc:
                logger.warning(
                    "[LLM] Provider '%s' unavailable (%s) — trying next provider...",
                    provider.name, exc,
                )
                last_error = exc
            except LLMError as exc:
                logger.warning(
                    "[LLM] Provider '%s' returned an error (%s) — trying next provider...",
                    provider.name, exc,
                )
                last_error = exc

        raise LLMUnavailableError(
            f"All LLM providers exhausted. Last error: {last_error}"
        ) from last_error


# Backward-compatible alias
LLMClient = FallbackLLMClient


# ── Module-level singleton ─────────────────────────────────────────────────────

_client: FallbackLLMClient | None = None


def get_llm_client() -> FallbackLLMClient:
    """Return a lazily-initialized FallbackLLMClient singleton.

    Registers whichever providers have API keys configured, in priority order:
      1. OpenAI   (OPENAI_API_KEY)
      2. Claude   (ANTHROPIC_API_KEY)
      3. Gemini   (GEMINI_API_KEY)
      4. Groq     (GROQ_API_KEY)

    At least one key must be set; multiple keys recommended for resilience.
    """
    global _client
    if _client is None:
        settings = get_settings()
        providers: list[BaseLLMProvider] = []

        if settings.openai_api_key:
            providers.append(OpenAIProvider(api_key=settings.openai_api_key))
            logger.info("[LLM] OpenAI provider registered (primary)")

        if settings.anthropic_api_key:
            providers.append(ClaudeProvider(api_key=settings.anthropic_api_key))
            logger.info("[LLM] Claude provider registered (%s)", "fallback" if providers else "primary")

        if settings.gemini_api_key:
            providers.append(GeminiProvider(api_key=settings.gemini_api_key))
            logger.info("[LLM] Gemini provider registered (%s)", "fallback" if providers else "primary")

        if settings.groq_api_key:
            providers.append(GroqProvider(api_key=settings.groq_api_key))
            logger.info("[LLM] Groq provider registered (%s)", "fallback" if providers else "primary")

        if not providers:
            raise LLMUnavailableError(
                "No LLM API keys configured. "
                "Set OPENAI_API_KEY, ANTHROPIC_API_KEY, GEMINI_API_KEY, or GROQ_API_KEY in your .env file."
            )

        _client = FallbackLLMClient(providers)
    return _client
