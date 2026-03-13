"""Base connector interface for enterprise system integrations."""

from __future__ import annotations

import abc
import logging
from typing import Any

from app.auth.manager import AuthSession

logger = logging.getLogger(__name__)


class BaseConnector(abc.ABC):
    """
    Abstract interface for enterprise system connectors.

    Each connector handles:
    - Authentication (via AuthManager)
    - Data extraction with pagination
    - Rate limiting and retry logic
    - Data normalization to common format
    """

    system_name: str = "base"
    category: str = "unknown"

    def __init__(self, auth_session: AuthSession | None = None):
        self.auth_session = auth_session
        self._rate_limit_remaining: int = 999
        self._rate_limit_reset: float = 0

    @abc.abstractmethod
    async def authenticate(self, credentials: dict) -> AuthSession:
        """Establish an authenticated session."""
        ...

    @abc.abstractmethod
    async def extract(self, query: dict) -> list[dict]:
        """
        Extract data based on a query specification.

        Args:
            query: Dict specifying what data to extract.
                   e.g., {"type": "pipeline_data", "date_range": "last_12_months"}

        Returns:
            List of normalized data records.
        """
        ...

    @abc.abstractmethod
    async def validate(self, data: list[dict]) -> dict:
        """
        Validate extracted data for completeness and consistency.

        Returns:
            Validation report dict.
        """
        ...

    async def disconnect(self) -> None:
        """Close the connection and clean up resources."""
        if self.auth_session:
            await self.auth_session.close()

    async def health_check(self) -> bool:
        """Check if the connector can reach the external system."""
        return self.auth_session is not None and self.auth_session.is_active
