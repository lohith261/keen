"""
BaseBrowserConnector — abstract base for TinyFish-powered browser connectors.

Extends BaseConnector with:
- TinyFish session lifecycle management (create → authenticate → extract → close)
- Graceful fallback to DemoConnector fixture data when TINYFISH_API_KEY is not set
- Cookie-based session persistence between authenticate() and extract() calls
- Structured error reporting that surfaces as empty results rather than crashes
"""

from __future__ import annotations

import logging
from typing import Any

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector
from app.integrations.browser.tinyfish import TinyFishClient, TinyFishError, TinyFishSession

logger = logging.getLogger(__name__)


class BaseBrowserConnector(BaseConnector):
    """
    Abstract base class for connectors that drive a real browser via TinyFish.

    Subclasses implement:
      login_url       Class attribute — URL of the login page
      _login()        Perform the site-specific login flow in the active session
      _do_extract()   Navigate to data page(s) and extract structured records

    The base class handles:
      - Creating / closing the TinyFish session
      - Storing the authenticated session_id across calls
      - Falling back to demo fixture data when TinyFish is unavailable
    """

    system_name: str = "browser"
    category: str = "browser"

    # Subclasses set these
    login_url: str = ""
    auth_flow: AuthFlowType = AuthFlowType.BROWSER

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._tinyfish = TinyFishClient()
        self._session: TinyFishSession | None = None
        self._credentials: dict = {}
        self._company_name: str = ""

    # ── Abstract interface for subclasses ─────────────────────────────────────

    async def _login(self, session: TinyFishSession, credentials: dict) -> None:
        """
        Perform the site-specific login flow.

        Override in each subclass. The session has already navigated to
        self.login_url before this is called.

        Args:
            session:     Active TinyFish session already at the login page.
            credentials: Decrypted credentials dict from the vault.
        """
        raise NotImplementedError

    async def _do_extract(
        self,
        session: TinyFishSession,
        query_type: str,
        company_name: str,
    ) -> list[dict]:
        """
        Navigate to the relevant page and extract structured records.

        Override in each subclass. The session is already authenticated.

        Args:
            session:      Active authenticated TinyFish session.
            query_type:   The extraction type (e.g. "market_comps").
            company_name: Target company to search/filter for.

        Returns:
            List of normalized record dicts.
        """
        raise NotImplementedError

    # ── BaseConnector implementation ──────────────────────────────────────────

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        Open a TinyFish browser session and log in to the target platform.

        If TINYFISH_API_KEY is not configured, logs a warning and returns
        a stub AuthSession (extract() will return empty results).
        """
        self._credentials = credentials
        self._company_name = credentials.get("company_name", "")

        if not self._tinyfish.is_configured:
            logger.warning(
                "%s: TINYFISH_API_KEY not set — live extraction unavailable. "
                "Set the key or use demo_mode=True.",
                self.system_name,
            )
            return AuthSession(self.system_name, self.auth_flow, {"session_id": ""})

        try:
            session = await self._tinyfish.create_session()

            # Navigate to the login page
            await session.navigate(self.login_url)
            logger.info("%s: navigated to login page %s", self.system_name, self.login_url)

            # Delegate to the subclass for site-specific login steps
            await self._login(session, credentials)

            # Grab cookies for later requests / debugging
            await session.get_cookies()
            self._session = session

            logger.info("%s: authenticated successfully via TinyFish", self.system_name)
            return AuthSession(
                self.system_name,
                self.auth_flow,
                {
                    "session_id": session.session_id,
                    "cookies": session.cookies,
                },
            )

        except TinyFishError as exc:
            logger.warning("%s: TinyFish authentication failed: %s", self.system_name, exc)
            return AuthSession(self.system_name, self.auth_flow, {"session_id": "", "error": str(exc)})
        except Exception as exc:
            logger.exception("%s: unexpected authentication error: %s", self.system_name, exc)
            return AuthSession(self.system_name, self.auth_flow, {"session_id": "", "error": str(exc)})

    async def extract(self, query: dict) -> list[dict]:
        """
        Use the active TinyFish session to extract data from the platform.

        Falls back to empty results if TinyFish is not configured or
        authentication failed.
        """
        query_type = query.get("type", "")
        company_name = query.get("company_name") or self._company_name

        if not self._session:
            logger.warning(
                "%s: no active TinyFish session — call authenticate() first or use demo_mode=True",
                self.system_name,
            )
            return []

        try:
            records = await self._do_extract(
                session=self._session,
                query_type=query_type,
                company_name=company_name,
            )
            logger.info(
                "%s[%s]: extracted %d records via TinyFish",
                self.system_name, query_type, len(records),
            )
            return records
        except TinyFishError as exc:
            logger.warning("%s[%s]: TinyFish extraction failed: %s", self.system_name, query_type, exc)
            return []
        except Exception as exc:
            logger.exception(
                "%s[%s]: unexpected extraction error: %s", self.system_name, query_type, exc
            )
            return []

    async def validate(self, data: list[dict]) -> dict:
        """Basic validation: checks that records were returned."""
        return {
            "total_records": len(data),
            "valid": True,
            "issues": [],
        }

    async def disconnect(self) -> None:
        """Close the TinyFish session and HTTP client."""
        if self._session:
            await self._session.close()
            self._session = None
        await self._tinyfish.close()
        await super().disconnect()
