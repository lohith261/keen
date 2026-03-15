"""
BaseBrowserConnector — abstract base for TinyFish-powered browser connectors.

Architecture: TinyFish is a single-shot API.  Each extract() call composes
a complete natural-language goal (login + navigate + extract) and sends it
as one POST to /v1/automation/run-sse.  There is no persistent session state.

Subclasses implement:
  login_url       Class attribute — URL of the login page
  _build_goal()   Returns a complete NL goal for login + extraction per query type
"""

from __future__ import annotations

import logging
from typing import Any

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector
from app.integrations.browser.tinyfish import TinyFishClient, TinyFishError

logger = logging.getLogger(__name__)


class BaseBrowserConnector(BaseConnector):
    """
    Abstract base class for connectors that drive a real browser via TinyFish.

    Each extraction call sends ONE goal to TinyFish that covers:
      1. Navigating to the login page (self.login_url)
      2. Logging in with the provided credentials
      3. Navigating to the target data page(s)
      4. Extracting structured JSON and returning it

    Subclasses implement:
      login_url      Class attribute — starting URL (typically the login page)
      _build_goal()  Returns a complete NL goal string per query_type
    """

    system_name: str = "browser"
    category: str = "browser"

    # Subclasses set this
    login_url: str = ""
    auth_flow: AuthFlowType = AuthFlowType.BROWSER

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tinyfish = TinyFishClient()
        self._credentials: dict = {}
        self._company_name: str = ""

    # ── Abstract interface for subclasses ─────────────────────────────────────

    def _build_goal(
        self,
        query_type: str,
        company_name: str,
        credentials: dict,
    ) -> str:
        """
        Build a complete natural-language goal for TinyFish.

        The goal must describe ALL of:
          1. How to log in (which fields to fill, which button to click)
          2. Where to navigate after login
          3. What data to extract
          4. What JSON structure to return

        Args:
            query_type:   Extraction type (e.g. "market_comps").
            company_name: Target company name.
            credentials:  Decrypted credentials dict (username, password, etc.).

        Returns:
            A detailed natural-language goal string for TinyFish.
        """
        raise NotImplementedError(
            f"{self.__class__.__name__} must implement _build_goal()"
        )

    # ── BaseConnector implementation ──────────────────────────────────────────

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        Store credentials for later use in extract().

        No network call is made here — TinyFish handles login as part of
        each extraction goal.
        """
        self._credentials = credentials
        self._company_name = credentials.get("company_name", "")

        if not self._tinyfish.is_configured:
            logger.warning(
                "%s: TINYFISH_API_KEY not set — live extraction unavailable. "
                "Set the key or use demo_mode=True.",
                self.system_name,
            )
            return AuthSession(
                self.system_name, self.auth_flow, {"configured": False}
            )

        logger.info(
            "%s: credentials stored (username=%s), ready for extraction",
            self.system_name,
            credentials.get("username", "<none>"),
        )
        return AuthSession(self.system_name, self.auth_flow, {"configured": True})

    async def extract(self, query: dict) -> list[dict]:
        """
        Compose a full login+navigate+extract goal and execute it via TinyFish.

        Each call is an independent, stateless TinyFish run. The goal string
        contains everything TinyFish needs to log in and extract data.
        """
        query_type = query.get("type", "")
        company_name = query.get("company_name") or self._company_name

        if not self._tinyfish.is_configured:
            logger.warning(
                "%s[%s]: TINYFISH_API_KEY not set — returning empty results",
                self.system_name,
                query_type,
            )
            return []

        if not self._credentials:
            logger.warning(
                "%s[%s]: no credentials — call authenticate() first",
                self.system_name,
                query_type,
            )
            return []

        try:
            goal = self._build_goal(query_type, company_name, self._credentials)
            logger.info(
                "%s[%s]: submitting TinyFish goal (%d chars) starting at %s",
                self.system_name,
                query_type,
                len(goal),
                self.login_url,
            )

            result = await self._tinyfish.run(
                url=self.login_url,
                goal=goal,
            )

            # Normalize to list[dict]
            if isinstance(result, list):
                records = [r for r in result if isinstance(r, dict)]
            elif isinstance(result, dict):
                records = [result]
            else:
                logger.warning(
                    "%s[%s]: unexpected result type %s", self.system_name, query_type, type(result)
                )
                records = []

            logger.info(
                "%s[%s]: extracted %d record(s) via TinyFish",
                self.system_name,
                query_type,
                len(records),
            )
            return records

        except TinyFishError as exc:
            logger.warning(
                "%s[%s]: TinyFish error: %s", self.system_name, query_type, exc
            )
            return []
        except Exception as exc:
            logger.exception(
                "%s[%s]: unexpected error during extraction: %s",
                self.system_name,
                query_type,
                exc,
            )
            return []

    async def validate(self, data: list[dict]) -> dict:
        """Basic validation — checks that records were returned."""
        return {
            "total_records": len(data),
            "valid": True,
            "issues": [],
        }

    async def disconnect(self) -> None:
        """Nothing to close — TinyFish calls are stateless."""
        await super().disconnect()
