"""Reusable async LLM client wrapping the Anthropic SDK."""

from __future__ import annotations

import json
import logging
import re
import time

import anthropic

from app.config import get_settings
from app.llm.exceptions import LLMError, LLMParseError, LLMUnavailableError

logger = logging.getLogger(__name__)

DEFAULT_MODEL = "claude-sonnet-4-20250514"


class LLMClient:
    """Thin wrapper around AsyncAnthropic with JSON parsing and retry logic."""

    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self.model = model

    async def complete_json(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.2,
        model: str | None = None,
    ) -> dict:
        """Send a message and parse the response as JSON.

        Strips markdown fences if present. Retries once on parse failure.
        """
        raw = await self._send(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )
        try:
            return self._parse_json(raw)
        except LLMParseError:
            # Retry with explicit JSON instruction
            logger.warning("JSON parse failed, retrying with explicit instruction")
            raw = await self._send(
                system_prompt,
                (
                    "Your previous response was not valid JSON. "
                    "Respond ONLY with valid JSON — no markdown, no commentary.\n\n"
                    + user_prompt
                ),
                max_tokens=max_tokens,
                temperature=0.1,
                model=model,
            )
            return self._parse_json(raw)

    async def complete_text(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int = 4096,
        temperature: float = 0.3,
        model: str | None = None,
    ) -> str:
        """Send a message and return the plain-text response."""
        return await self._send(
            system_prompt,
            user_prompt,
            max_tokens=max_tokens,
            temperature=temperature,
            model=model,
        )

    # ── Internal helpers ──────────────────────────────────

    async def _send(
        self,
        system_prompt: str,
        user_prompt: str,
        *,
        max_tokens: int,
        temperature: float,
        model: str | None = None,
    ) -> str:
        """Call the Anthropic messages API."""
        use_model = model or self.model
        start = time.monotonic()
        try:
            response = await self._client.messages.create(
                model=use_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            text = response.content[0].text
            elapsed = time.monotonic() - start
            logger.info(
                "LLM call: model=%s prompt_len=%d response_len=%d latency=%.1fs",
                use_model,
                len(user_prompt),
                len(text),
                elapsed,
            )
            return text
        except anthropic.AuthenticationError as exc:
            raise LLMUnavailableError(f"Invalid API key: {exc}") from exc
        except anthropic.RateLimitError:
            # Retry once after a short pause
            logger.warning("Rate limited, retrying in 2s")
            import asyncio

            await asyncio.sleep(2)
            try:
                response = await self._client.messages.create(
                    model=use_model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt,
                    messages=[{"role": "user", "content": user_prompt}],
                )
                return response.content[0].text
            except anthropic.APIError as exc:
                raise LLMUnavailableError(f"API error after retry: {exc}") from exc
        except anthropic.APIError as exc:
            raise LLMError(f"Anthropic API error: {exc}") from exc

    @staticmethod
    def _parse_json(text: str) -> dict:
        """Extract and parse JSON from LLM response text."""
        # Strip markdown code fences if present
        cleaned = re.sub(r"^```(?:json)?\s*\n?", "", text.strip())
        cleaned = re.sub(r"\n?```\s*$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError as exc:
            # Last resort: try to find a JSON object in the text
            match = re.search(r"\{[\s\S]*\}", cleaned)
            if match:
                try:
                    return json.loads(match.group())
                except json.JSONDecodeError:
                    pass
            raise LLMParseError(f"Could not parse JSON: {exc}") from exc


# ── Module-level singleton ────────────────────────────────

_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Return a lazily-initialized LLMClient singleton."""
    global _client
    if _client is None:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise LLMUnavailableError(
                "ANTHROPIC_API_KEY is not set. Configure it in .env to enable LLM features."
            )
        _client = LLMClient(api_key=settings.anthropic_api_key)
    return _client
