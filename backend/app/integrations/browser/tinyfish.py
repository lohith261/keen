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
  Server-Sent Events (SSE) stream. The final COMPLETE event carries
  `resultJson` (the extracted data as a JSON string or dict).

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


def _parse_sse_stream(raw: str) -> Any:
    """
    Parse an SSE stream string and return the resultJson from the COMPLETE event.

    TinyFish SSE format:
      data: {"type":"progress","message":"..."}
      data: {"type":"complete","status":"COMPLETED","resultJson":{...}}
      data: {"type":"error","message":"..."}
    """
    result_json: Any = None
    last_data: dict = {}

    for line in raw.splitlines():
        line = line.strip()
        if not line.startswith("data:"):
            continue
        payload_str = line[len("data:"):].strip()
        if not payload_str:
            continue
        try:
            payload = json.loads(payload_str)
        except json.JSONDecodeError:
            continue

        last_data = payload
        event_type = (payload.get("type") or "").lower()

        # Accept "complete" or "COMPLETE" or status == "COMPLETED"
        if event_type in ("complete", "completed") or payload.get("status") == "COMPLETED":
            # resultJson may be a pre-parsed dict/list or a JSON string
            rj = payload.get("resultJson") or payload.get("result") or payload.get("data")
            if isinstance(rj, str):
                try:
                    rj = json.loads(rj)
                except json.JSONDecodeError:
                    pass
            result_json = rj

        elif event_type in ("error", "failed"):
            raise TinyFishError(
                f"TinyFish task failed: {payload.get('message') or payload_str[:200]}"
            )

    # If we got a result, return it
    if result_json is not None:
        return result_json

    # Try the last data block as a fallback (some versions don't use "complete" type)
    rj = last_data.get("resultJson") or last_data.get("result") or last_data.get("data")
    if rj is not None:
        if isinstance(rj, str):
            try:
                rj = json.loads(rj)
            except json.JSONDecodeError:
                pass
        return rj

    raise TinyFishError(
        f"No COMPLETE event found in TinyFish SSE stream. Last event: {last_data}"
    )


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
    ) -> Any:
        """
        Execute a browser automation task and return the extracted JSON data.

        Args:
            url:            Starting URL (e.g. login page).
            goal:           Natural-language description of what to do and
                            what JSON structure to return.
            proxy_config:   Optional proxy settings, e.g. {"enabled": True}.
            browser_profile: "stealth" (default) for bot-protected sites.

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
                    if response.status_code == 401:
                        raise TinyFishError(
                            "TinyFish: 401 Unauthorized — check your TINYFISH_API_KEY"
                        )
                    if response.status_code == 403:
                        raise TinyFishError(
                            f"TinyFish: 403 Forbidden — {await response.aread()}"
                        )
                    if response.status_code >= 400:
                        body = (await response.aread()).decode("utf-8", errors="replace")
                        raise TinyFishError(
                            f"TinyFish: HTTP {response.status_code} — {body[:300]}"
                        )

                    raw = (await response.aread()).decode("utf-8", errors="replace")

                result = _parse_sse_stream(raw)
                logger.info("TinyFish: task completed successfully")
                return result

            except httpx.TimeoutException as exc:
                raise TinyFishError(f"TinyFish request timed out: {exc}") from exc
            except httpx.ConnectError as exc:
                raise TinyFishError(f"TinyFish connection error: {exc}") from exc
