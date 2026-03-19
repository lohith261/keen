"""
TinyFish AI browser automation client.

TinyFish takes a URL + natural-language goal and returns structured JSON.
It handles navigation, authentication, dynamic content, and multi-step
flows autonomously — one API call per task.

Endpoint:
  POST https://agent.tinyfish.ai/v1/automation/run-sse

Authentication:
  X-API-Key: <your_tinyfish_api_key>

Response:
  Server-Sent Events (SSE) stream. Events include:
    STARTED       — task accepted, browser is booting
    STREAMING_URL — live browser view URL (call on_streaming_url callback)
    PROGRESS      — intermediate progress messages
    HEARTBEAT     — keep-alive
    COMPLETE      — carries `resultJson` (extracted data as JSON string or dict)
    ERROR / FAILED — task failed

Environment variables:
  TINYFISH_API_KEY    Required. Obtain at https://agent.tinyfish.ai/api-keys
  TINYFISH_BASE_URL   Defaults to https://agent.tinyfish.ai

Docs: https://docs.tinyfish.ai
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_SSE_ENDPOINT = "/v1/automation/run-sse"
_TIMEOUT = httpx.Timeout(connect=15.0, read=300.0, write=30.0, pool=5.0)


class TinyFishError(Exception):
    """Raised on TinyFish API errors, auth failures, or task failures."""


class TinyFishClient:
    """
    Thin async client for the TinyFish web automation API.

    Usage:
        client = TinyFishClient()
        if client.is_configured:
            data = await client.run(
                url="https://bloomberg.com/login",
                goal="Log in with username 'user' password 'pw', "
                     "then extract peer comparison table as JSON",
                on_streaming_url=lambda url: print(f"Live view: {url}"),
            )
    """

    def __init__(self, api_key: str = "", base_url: str = "") -> None:
        settings = get_settings()
        self._api_key = api_key or settings.tinyfish_api_key
        self._base_url = (base_url or settings.tinyfish_base_url or "https://agent.tinyfish.ai").rstrip("/")

    @property
    def is_configured(self) -> bool:
        return bool(self._api_key)

    async def run(
        self,
        url: str,
        goal: str,
        proxy_config: dict | None = None,
        browser_profile: str = "stealth",
        on_streaming_url: Any | None = None,
    ) -> Any:
        """
        Execute a browser automation task and return the extracted JSON data.

        Processes the TinyFish SSE stream incrementally so that the live
        browser streaming URL is surfaced to callers as soon as TinyFish
        emits the STREAMING_URL event — long before extraction completes.

        Args:
            url:               Starting URL (e.g. login page).
            goal:              Natural-language description of what to do and
                               what JSON structure to return.
            proxy_config:      Optional proxy settings, e.g. {"enabled": True}.
            browser_profile:   "stealth" (default) for bot-protected sites.
            on_streaming_url:  Optional async callable(url: str) invoked as soon
                               as TinyFish emits the live browser stream URL.
                               Use this to show users a real-time browser view.

        Returns:
            Parsed Python object from resultJson (list, dict, etc.).

        Raises:
            TinyFishError: if the API returns an error or the task fails.
        """
        if not self.is_configured:
            raise TinyFishError(
                "TINYFISH_API_KEY is not set. "
                "Configure it as an environment variable or use demo_mode=True."
            )

        payload: dict[str, Any] = {
            "url": url,
            "goal": goal,
            "browser_profile": browser_profile,
        }
        if proxy_config is not None:
            payload["proxy_config"] = proxy_config
        else:
            payload["proxy_config"] = {"enabled": False}

        logger.info("TinyFish: running task at %s (goal length=%d chars)", url, len(goal))

        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "X-API-Key": self._api_key,
                "Content-Type": "application/json",
                "Accept": "text/event-stream",
            },
            timeout=_TIMEOUT,
        ) as client:
            try:
                async with client.stream("POST", _SSE_ENDPOINT, json=payload) as response:
                    # For error status codes, read body first then raise
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace")
                        if response.status_code == 401:
                            raise TinyFishError(
                                "TinyFish: 401 Unauthorized — check your TINYFISH_API_KEY"
                            )
                        if response.status_code == 403:
                            raise TinyFishError(
                                f"TinyFish: 403 Forbidden — {body}"
                            )
                        raise TinyFishError(
                            f"TinyFish: HTTP {response.status_code} — {body[:300]}"
                        )

                    # Process SSE stream line by line for real-time streaming URL capture
                    result_json: Any = None
                    last_data: dict = {}

                    async for line in response.aiter_lines():
                        line = line.strip()
                        if not line.startswith("data:"):
                            continue
                        payload_str = line[len("data:"):].strip()
                        if not payload_str:
                            continue
                        try:
                            event_payload = json.loads(payload_str)
                        except json.JSONDecodeError:
                            continue

                        last_data = event_payload
                        event_type = (event_payload.get("type") or "").lower()

                        # ── Live browser streaming URL ────────────────────────
                        # TinyFish emits this early in the session so callers can
                        # display a live browser view while extraction is in progress.
                        if "streaming" in event_type or event_type in ("stream", "monitor"):
                            s_url = (
                                event_payload.get("url")
                                or event_payload.get("streamingUrl")
                                or event_payload.get("streaming_url")
                                or event_payload.get("streamUrl")
                            )
                            if s_url and on_streaming_url:
                                logger.info("TinyFish: live browser stream available at %s", s_url)
                                try:
                                    await on_streaming_url(s_url)
                                except Exception as cb_exc:
                                    logger.debug(
                                        "on_streaming_url callback error (non-fatal): %s", cb_exc
                                    )

                        # ── Task completion ────────────────────────────────────
                        if (
                            event_type in ("complete", "completed")
                            or event_payload.get("status") == "COMPLETED"
                        ):
                            rj = (
                                event_payload.get("resultJson")
                                or event_payload.get("result")
                                or event_payload.get("data")
                            )
                            if isinstance(rj, str):
                                try:
                                    rj = json.loads(rj)
                                except json.JSONDecodeError:
                                    pass
                            result_json = rj

                        # ── Task failure ──────────────────────────────────────
                        elif event_type in ("error", "failed"):
                            raise TinyFishError(
                                f"TinyFish task failed: "
                                f"{event_payload.get('message') or payload_str[:200]}"
                            )

                    if result_json is not None:
                        logger.info("TinyFish: task completed successfully")
                        return result_json

                    # Fallback: try the last SSE event as some versions don't use "complete" type
                    rj = (
                        last_data.get("resultJson")
                        or last_data.get("result")
                        or last_data.get("data")
                    )
                    if rj is not None:
                        if isinstance(rj, str):
                            try:
                                rj = json.loads(rj)
                            except json.JSONDecodeError:
                                pass
                        return rj

                    raise TinyFishError(
                        f"No COMPLETE event found in TinyFish SSE stream. "
                        f"Last event: {last_data}"
                    )

            except httpx.TimeoutException as exc:
                raise TinyFishError(f"TinyFish request timed out: {exc}") from exc
            except httpx.ConnectError as exc:
                raise TinyFishError(f"TinyFish connection error: {exc}") from exc
