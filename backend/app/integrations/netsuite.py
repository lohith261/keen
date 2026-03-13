"""
NetSuite ERP connector.

Extracts financial data — revenue, expenses, journal entries,
and balance sheet data via NetSuite SuiteTalk REST API.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)


class NetSuiteConnector(BaseConnector):
    """Connector for NetSuite ERP data extraction."""

    system_name = "netsuite"
    category = "erp"

    def __init__(self, account_id: str = "", **kwargs: Any):
        super().__init__(**kwargs)
        self.account_id = account_id
        self._client: httpx.AsyncClient | None = None

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        Authenticate to NetSuite via token-based auth.

        TODO: Implement NetSuite TBA (Token-Based Authentication):
        1. Use consumer key/secret + token key/secret
        2. Generate OAuth 1.0 signature
        3. Include in Authorization header
        """
        session = AuthSession(
            self.system_name,
            AuthFlowType.TOKEN,
            {
                "token": credentials.get("token", ""),
                "account_id": self.account_id,
            },
        )
        self.auth_session = session

        base_url = f"https://{self.account_id}.suitetalk.api.netsuite.com"
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers=session.get_headers(),
            timeout=60.0,
        )

        return session

    async def extract(self, query: dict) -> list[dict]:
        """
        Extract financial data from NetSuite.

        Supported query types:
        - revenue_data: Revenue by period
        - expense_records: Expense line items
        - journal_entries: GL journal entries
        - balance_sheet: Balance sheet snapshot
        """
        query_type = query.get("type", "revenue_data")

        # TODO: Execute SuiteQL queries via NetSuite REST API
        # endpoint = "/services/rest/query/v1/suiteql"
        # suiteql = f"SELECT * FROM transaction WHERE type = 'CustInvc' AND ..."
        # response = await self._client.post(endpoint, json={"q": suiteql})

        logger.info(f"Would extract {query_type} from NetSuite")
        return []

    async def validate(self, data: list[dict]) -> dict:
        """Validate extracted NetSuite data."""
        return {
            "total_records": len(data),
            "valid": True,
            "issues": [],
        }

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        await super().disconnect()
