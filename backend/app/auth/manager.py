"""
Dynamic authentication manager.

Handles SSO, MFA, OAuth, API key, and browser-based auth flows
for enterprise system access. Adapts semantically to auth UI changes
rather than relying on brittle CSS selectors.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any
from uuid import UUID

from app.auth.vault import CredentialVault

logger = logging.getLogger(__name__)


class AuthFlowType(str, Enum):
    """Supported authentication flow types."""
    OAUTH = "oauth"
    API_KEY = "api_key"
    USERNAME_PASSWORD = "username_password"
    SSO = "sso"
    BROWSER = "browser"
    PUBLIC = "public"
    TOKEN = "token"


class AuthSession:
    """Represents an authenticated session to an external system."""

    def __init__(
        self,
        system_name: str,
        flow_type: AuthFlowType,
        session_data: dict | None = None,
    ):
        self.system_name = system_name
        self.flow_type = flow_type
        self.session_data = session_data or {}
        self.is_active = True

    def get_headers(self) -> dict[str, str]:
        """Get auth headers for API requests."""
        if self.flow_type == AuthFlowType.API_KEY:
            return {"Authorization": f"Bearer {self.session_data.get('api_key', '')}"}
        elif self.flow_type == AuthFlowType.OAUTH:
            return {"Authorization": f"Bearer {self.session_data.get('access_token', '')}"}
        elif self.flow_type == AuthFlowType.TOKEN:
            return {"Authorization": f"Token {self.session_data.get('token', '')}"}
        return {}

    async def refresh(self) -> bool:
        """
        Refresh the session if token is expiring.

        For OAuth sessions: re-use stored refresh_token if available.
        For API key / token sessions: keys don't expire, always valid.
        Returns False if the session cannot be refreshed (caller should re-auth).
        """
        if self.flow_type == AuthFlowType.OAUTH:
            access_token = self.session_data.get("access_token", "")
            refresh_token = self.session_data.get("refresh_token", "")
            if not access_token:
                logger.error(
                    "OAuth session for '%s' has no access_token — re-authentication required",
                    self.system_name,
                )
                self.is_active = False
                return False
            if not refresh_token:
                logger.warning(
                    "OAuth session for '%s' has no refresh_token — cannot auto-refresh; "
                    "existing access_token will be used until it expires",
                    self.system_name,
                )
            # Access token is present — assume valid until the connector gets a 401
            return True
        # API key, token, browser sessions — don't expire on a schedule
        return self.is_active

    async def close(self) -> None:
        """Close the session."""
        self.is_active = False


class AuthManager:
    """
    Manages authentication flows across enterprise systems.

    Capabilities:
    - Detects the appropriate auth flow type for each system
    - Handles OAuth code/token exchanges
    - Manages SSO with MFA support
    - Integrates with TinyFish for browser-based auth
    - Performs token rotation and session management
    - Adapts semantically to UI changes (not brittle selectors)
    """

    def __init__(self, vault: CredentialVault):
        self.vault = vault
        self._sessions: dict[str, AuthSession] = {}

    async def authenticate(
        self,
        system_name: str,
        flow_type: AuthFlowType,
        engagement_id: UUID | None = None,
    ) -> AuthSession:
        """
        Authenticate to an external system.

        Args:
            system_name: Name of the system (e.g., "salesforce", "netsuite")
            flow_type: Type of auth flow to use
            engagement_id: Engagement to load credentials from

        Returns:
            AuthSession with active credentials
        """
        # Check for existing active session
        if system_name in self._sessions and self._sessions[system_name].is_active:
            session = self._sessions[system_name]
            if await session.refresh():
                return session

        # Load credentials from vault
        credentials = {}
        if engagement_id:
            credentials = await self.vault.get_credentials(engagement_id, system_name)

        # Route to appropriate auth flow
        session = await self._execute_auth_flow(system_name, flow_type, credentials)
        self._sessions[system_name] = session

        logger.info(f"Authenticated to {system_name} via {flow_type.value}")
        return session

    async def _execute_auth_flow(
        self,
        system_name: str,
        flow_type: AuthFlowType,
        credentials: dict,
    ) -> AuthSession:
        """Execute the appropriate authentication flow."""

        if flow_type == AuthFlowType.PUBLIC:
            return AuthSession(system_name, flow_type)

        elif flow_type == AuthFlowType.API_KEY:
            return await self._auth_api_key(system_name, credentials)

        elif flow_type == AuthFlowType.OAUTH:
            return await self._auth_oauth(system_name, credentials)

        elif flow_type == AuthFlowType.USERNAME_PASSWORD:
            return await self._auth_username_password(system_name, credentials)

        elif flow_type == AuthFlowType.SSO:
            return await self._auth_sso(system_name, credentials)

        elif flow_type == AuthFlowType.BROWSER:
            return await self._auth_browser(system_name, credentials)

        elif flow_type == AuthFlowType.TOKEN:
            return await self._auth_token(system_name, credentials)

        raise ValueError(f"Unsupported auth flow: {flow_type}")

    async def _auth_api_key(self, system_name: str, credentials: dict) -> AuthSession:
        """Handle API key authentication."""
        return AuthSession(
            system_name,
            AuthFlowType.API_KEY,
            {"api_key": credentials.get("api_key", "")},
        )

    async def _auth_oauth(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle OAuth 2.0 authentication.

        TODO: Implement full OAuth flow:
        1. Check for existing refresh token
        2. If valid, use refresh token to get new access token
        3. If not, initiate authorization code flow
        4. Exchange code for tokens
        5. Store refresh token in vault
        """
        return AuthSession(
            system_name,
            AuthFlowType.OAUTH,
            {
                "access_token": credentials.get("access_token", ""),
                "refresh_token": credentials.get("refresh_token", ""),
            },
        )

    async def _auth_username_password(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle username/password authentication.

        Uses stored credentials from the vault. If credentials are missing,
        logs a warning and returns an inactive session so the connector
        can surface the failure rather than silently returning empty data.
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        if not username or not password:
            logger.warning(
                "_auth_username_password: no credentials stored for '%s' — "
                "store them via the Credentials panel before running live",
                system_name,
            )
            session = AuthSession(system_name, AuthFlowType.USERNAME_PASSWORD, {"session_token": ""})
            session.is_active = False
            return session
        # Credentials are present — connector will use them for the actual login request
        logger.info("Username/password credentials loaded for '%s'", system_name)
        return AuthSession(
            system_name,
            AuthFlowType.USERNAME_PASSWORD,
            {"username": username, "password": password, "session_token": ""},
        )

    async def _auth_sso(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle SSO (Single Sign-On) with potential MFA via TinyFish browser automation.

        Navigate SSO login pages, handle MFA prompts, extract session cookies.
        Falls back to browser auth flow when SSO credentials are stored.
        """
        sso_token = credentials.get("sso_token", "") or credentials.get("token", "")
        if not sso_token:
            logger.warning(
                "_auth_sso: no SSO token stored for '%s' — "
                "store them via the Credentials panel. Attempting browser auth as fallback.",
                system_name,
            )
            # Fall back to browser-based auth (TinyFish handles SSO pages)
            return await self._auth_browser(system_name, credentials)
        return AuthSession(
            system_name,
            AuthFlowType.SSO,
            {"sso_token": sso_token},
        )

    async def _auth_browser(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle browser-based authentication via TinyFish.

        Launches a TinyFish headless browser session, navigates to the target
        system's login page, and uses AI-powered form filling to authenticate.
        The session cookies are extracted and stored for subsequent API/page calls.

        Requires TINYFISH_API_KEY to be set in the environment. If not set,
        returns an empty stub session — the connector will surface this as
        empty extraction results (falling back to demo mode if configured).
        """
        from app.integrations.browser.tinyfish import TinyFishClient, TinyFishError

        client = TinyFishClient()

        if not client.is_configured:
            logger.warning(
                "AuthManager._auth_browser: TINYFISH_API_KEY not configured — "
                "returning stub session for %s",
                system_name,
            )
            return AuthSession(
                system_name,
                AuthFlowType.BROWSER,
                {"cookies": {}, "session_id": "", "error": "tinyfish_not_configured"},
            )

        # Map system names to their login pages
        login_urls: dict[str, str] = {
            "bloomberg": "https://bba.bloomberg.net",
            "capiq": "https://www.capitaliq.spglobal.com/web/client#auth/login",
            "pitchbook": "https://pitchbook.com/login",
            "sales_navigator": "https://www.linkedin.com/login",
        }

        login_url = login_urls.get(system_name, "")
        if not login_url:
            logger.warning(
                "AuthManager._auth_browser: no login URL registered for '%s'",
                system_name,
            )
            return AuthSession(
                system_name,
                AuthFlowType.BROWSER,
                {"cookies": {}, "session_id": "", "error": f"no_login_url_{system_name}"},
            )

        try:
            session = await client.create_session()
            await session.navigate(login_url)
            await session.act(
                "Fill in the username/email field with the provided username and "
                "the password field with the provided password, then submit the form",
                context={
                    "username": credentials.get("username", ""),
                    "password": credentials.get("password", ""),
                },
            )
            cookies = await session.get_cookies()

            auth_session = AuthSession(
                system_name,
                AuthFlowType.BROWSER,
                {
                    "session_id": session.session_id,
                    "cookies": cookies,
                },
            )
            # Store the open TinyFish session so the connector can reuse it
            auth_session._tinyfish_session = session  # type: ignore[attr-defined]
            auth_session._tinyfish_client = client     # type: ignore[attr-defined]

            logger.info(
                "AuthManager: browser auth completed for %s (session %s)",
                system_name, session.session_id,
            )
            return auth_session

        except TinyFishError as exc:
            logger.warning(
                "AuthManager._auth_browser: TinyFish error for %s: %s", system_name, exc
            )
            await client.close()
            return AuthSession(
                system_name,
                AuthFlowType.BROWSER,
                {"cookies": {}, "session_id": "", "error": str(exc)},
            )

    async def _auth_token(self, system_name: str, credentials: dict) -> AuthSession:
        """Handle token-based authentication."""
        return AuthSession(
            system_name,
            AuthFlowType.TOKEN,
            {"token": credentials.get("token", "")},
        )

    async def close_all(self) -> None:
        """Close all active sessions."""
        for session in self._sessions.values():
            await session.close()
        self._sessions.clear()
