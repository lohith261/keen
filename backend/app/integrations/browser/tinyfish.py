"""
TinyFish AI browser automation client.

TinyFish provides AI-powered browser sessions that can navigate websites,
fill forms, handle authentication flows, and extract structured data using
natural language instructions rather than brittle CSS selectors.

API pattern:
  POST   /v1/sessions                    Create a new browser session
  POST   /v1/sessions/{id}/navigate      Navigate to a URL
  POST   /v1/sessions/{id}/act           Execute a natural-language action
  POST   /v1/sessions/{id}/extract       Extract structured data
  GET    /v1/sessions/{id}/cookies       Retrieve session cookies
  POST   /v1/sessions/{id}/screenshot    Take a screenshot (for debugging)
  DELETE /v1/sessions/{id}              Close and release the session

Sessions are stateful — cookies, local-storage and JS context persist
across navigate/act/extract calls within the same session.

Configure via environment variables:
  TINYFISH_API_KEY      Required for live mode  (e.g. tf-xxxx)
  TINYFISH_BASE_URL     Defaults to https://api.tinyfish.io
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=30.0, pool=5.0)


class TinyFishError(Exception):
    """Raised when the TinyFish API returns an error or times out."""


class TinyFishSession:
    """
    Represents an active TinyFish browser session.

    Keeps the session_id and provides helper coroutines for common operations.
    Always call close() (or use as an async context manager) when done.
    """

    def __init__(self, client: TinyFishClient, session_id: str) -> None:
        self._client = client
        self.session_id = session_id
        self.cookies: list[dict] = []

    # ── Navigation ────────────────────────────────────────────────────────────

    async def navigate(self, url: str, wait_for: str = "networkidle") -> dict:
        """
        Navigate to a URL and wait for the page to settle.

        Args:
            url:       Target URL.
            wait_for:  Page-ready signal: "networkidle" | "load" | "domcontentloaded"

        Returns:
            API response dict with at least {"status": "ok", "current_url": ...}.
        """
        return await self._client._post(
            f"/v1/sessions/{self.session_id}/navigate",
            {"url": url, "wait_for": wait_for},
        )

    # ── Interaction ───────────────────────────────────────────────────────────

    async def act(self, instruction: str, context: dict | None = None) -> dict:
        """
        Execute a natural-language browser action.

        Examples:
          "Click the 'Sign In' button"
          "Type 'user@example.com' into the email field and press Tab"
          "Wait for the loading spinner to disappear, then click 'Continue'"

        Args:
            instruction: Human-readable action to perform.
            context:     Optional extra data available to the AI (e.g. credentials).

        Returns:
            API response dict with {"status": "ok", "actions_performed": [...]}.
        """
        payload: dict[str, Any] = {"instruction": instruction}
        if context:
            payload["context"] = context
        return await self._client._post(
            f"/v1/sessions/{self.session_id}/act",
            payload,
        )

    # ── Extraction ────────────────────────────────────────────────────────────

    async def extract(
        self,
        instruction: str,
        schema: dict | None = None,
        paginate: bool = False,
    ) -> Any:
        """
        Extract structured data from the current page.

        Args:
            instruction: What to extract, in natural language.
            schema:      Optional JSON Schema describing the expected output shape.
                         If provided, TinyFish will conform its output to the schema.
            paginate:    If True, automatically click "Next" / "Load more" buttons
                         and accumulate results across pages.

        Returns:
            Extracted data — structure depends on schema. Typically a list or dict.
        """
        payload: dict[str, Any] = {
            "instruction": instruction,
            "paginate": paginate,
        }
        if schema:
            payload["schema"] = schema
        response = await self._client._post(
            f"/v1/sessions/{self.session_id}/extract",
            payload,
        )
        return response.get("data", response)

    # ── Cookies ───────────────────────────────────────────────────────────────

    async def get_cookies(self) -> list[dict]:
        """Retrieve all cookies from the current browser session."""
        response = await self._client._get(f"/v1/sessions/{self.session_id}/cookies")
        self.cookies = response.get("cookies", [])
        return self.cookies

    # ── Lifecycle ─────────────────────────────────────────────────────────────

    async def close(self) -> None:
        """Close and release the browser session."""
        try:
            await self._client._delete(f"/v1/sessions/{self.session_id}")
            logger.debug("TinyFish: closed session %s", self.session_id)
        except Exception as exc:
            logger.warning("TinyFish: error closing session %s: %s", self.session_id, exc)

    async def __aenter__(self) -> TinyFishSession:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()


class TinyFishClient:
    """
    HTTP client for the TinyFish browser automation API.

    Obtain a session with create_session() and use it to navigate,
    interact with, and extract data from websites.

    Usage:
        client = TinyFishClient()
        async with client:
            session = await client.create_session()
            async with session:
                await session.navigate("https://example.com/login")
                await session.act("Fill in email 'user@co.com' and password 'pw', click Login")
                data = await session.extract("Extract all table rows")
    """

    def __init__(
        self,
        api_key: str = "",
        base_url: str = "",
    ) -> None:
        settings = get_settings()
        self._api_key = api_key or settings.tinyfish_api_key
        self._base_url = (base_url or settings.tinyfish_base_url).rstrip("/")
        self._http: httpx.AsyncClient | None = None

    @property
    def is_configured(self) -> bool:
        """True if an API key is available (live mode possible)."""
        return bool(self._api_key)

    def _build_client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(
            base_url=self._base_url,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "X-Client": "KEEN/0.1.0",
            },
            timeout=_TIMEOUT,
        )

    async def _get_http(self) -> httpx.AsyncClient:
        if self._http is None or self._http.is_closed:
            self._http = self._build_client()
        return self._http

    async def _post(self, path: str, body: dict) -> dict:
        client = await self._get_http()
        try:
            response = await client.post(path, json=body)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise TinyFishError(
                f"TinyFish API error {exc.response.status_code} at {path}: "
                f"{exc.response.text[:200]}"
            ) from exc
        except httpx.TimeoutException as exc:
            raise TinyFishError(f"TinyFish timed out at {path}") from exc

    async def _get(self, path: str) -> dict:
        client = await self._get_http()
        try:
            response = await client.get(path)
            response.raise_for_status()
            return response.json()
        except httpx.HTTPStatusError as exc:
            raise TinyFishError(
                f"TinyFish API error {exc.response.status_code} at {path}: "
                f"{exc.response.text[:200]}"
            ) from exc

    async def _delete(self, path: str) -> dict:
        client = await self._get_http()
        try:
            response = await client.delete(path)
            response.raise_for_status()
            return response.json()
        except Exception:
            return {}

    async def create_session(
        self,
        headless: bool = True,
        viewport: dict | None = None,
        proxy: dict | None = None,
    ) -> TinyFishSession:
        """
        Launch a new headless browser session.

        Args:
            headless:  Run browser without a visible window (default True).
            viewport:  Browser window size, e.g. {"width": 1920, "height": 1080}.
            proxy:     Optional proxy config, e.g. {"server": "http://proxy:8080"}.

        Returns:
            TinyFishSession ready for navigation.
        """
        if not self.is_configured:
            raise TinyFishError(
                "TINYFISH_API_KEY is not configured. "
                "Set it as an environment variable or use demo_mode=True."
            )

        payload: dict[str, Any] = {
            "headless": headless,
            "viewport": viewport or {"width": 1440, "height": 900},
        }
        if proxy:
            payload["proxy"] = proxy

        response = await self._post("/v1/sessions", payload)
        session_id = response.get("session_id") or response.get("id")
        if not session_id:
            raise TinyFishError(
                f"TinyFish session creation failed — no session_id in response: {response}"
            )

        logger.info("TinyFish: created session %s", session_id)
        return TinyFishSession(self, session_id)

    async def close(self) -> None:
        """Close the underlying HTTP client."""
        if self._http and not self._http.is_closed:
            await self._http.aclose()

    async def __aenter__(self) -> TinyFishClient:
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()
