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
        """Refresh the session if token is expiring."""
        # TODO: Implement token refresh logic
        return True

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
        """Handle username/password authentication."""
        # TODO: POST to login endpoint, get session cookie/token
        return AuthSession(
            system_name,
            AuthFlowType.USERNAME_PASSWORD,
            {"session_token": ""},
        )

    async def _auth_sso(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle SSO (Single Sign-On) with potential MFA.

        TODO: This is where TinyFish browser automation shines —
        navigate SSO login pages, handle MFA prompts, extract session cookies.
        Uses semantic page understanding rather than brittle selectors.
        """
        return AuthSession(
            system_name,
            AuthFlowType.SSO,
            {"sso_token": ""},
        )

    async def _auth_browser(self, system_name: str, credentials: dict) -> AuthSession:
        """
        Handle browser-based authentication via TinyFish.

        For systems like Bloomberg Terminal, PitchBook, Capital IQ
        that require browser interaction for login.

        TODO: Integrate with TinyFish API:
        1. Launch headless browser session via TinyFish
        2. Navigate to login page
        3. Use semantic understanding to fill credentials
        4. Handle CAPTCHA / MFA if needed
        5. Extract authenticated session cookies
        """
        return AuthSession(
            system_name,
            AuthFlowType.BROWSER,
            {"cookies": {}, "session_id": ""},
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
