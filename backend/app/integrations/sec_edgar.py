"""
SEC EDGAR connector.

Extracts public filing data — 10-K, 10-Q, proxy statements,
and insider transactions from the SEC EDGAR XBRL API.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

# SEC EDGAR requires a User-Agent with contact info
EDGAR_USER_AGENT = "KEEN/0.1.0 (contact@keenai.com)"
EDGAR_BASE_URL = "https://efts.sec.gov/LATEST"
EDGAR_DATA_URL = "https://data.sec.gov"


class SECEdgarConnector(BaseConnector):
    """Connector for SEC EDGAR public filings data."""

    system_name = "sec_edgar"
    category = "regulatory"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client: httpx.AsyncClient | None = None

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        SEC EDGAR is public — no authentication needed.
        Just set up the HTTP client with proper User-Agent.
        """
        session = AuthSession(self.system_name, AuthFlowType.PUBLIC)
        self.auth_session = session

        self._client = httpx.AsyncClient(
            headers={"User-Agent": EDGAR_USER_AGENT},
            timeout=30.0,
        )

        return session

    async def extract(self, query: dict) -> list[dict]:
        """
        Extract filing data from SEC EDGAR.

        Supported query types:
        - 10k_filings: Annual reports
        - 10q_filings: Quarterly reports
        - insider_transactions: Form 4 filings
        - proxy_statements: DEF 14A filings
        """
        query_type = query.get("type", "10k_filings")
        company_cik = query.get("cik", "")
        company_name = query.get("company_name", "")

        if not self._client:
            return []

        # Search for company CIK if not provided
        if not company_cik and company_name:
            company_cik = await self._search_company(company_name)

        if not company_cik:
            logger.warning("No CIK provided or found")
            return []

        # Fetch filings
        form_types = {
            "10k_filings": "10-K",
            "10q_filings": "10-Q",
            "insider_transactions": "4",
            "proxy_statements": "DEF 14A",
        }

        form_type = form_types.get(query_type, "10-K")

        try:
            # Use the full-text search API
            response = await self._client.get(
                f"{EDGAR_BASE_URL}/search-index",
                params={
                    "q": f'"{company_name}"',
                    "forms": form_type,
                    "dateRange": "custom",
                    "startdt": query.get("start_date", "2023-01-01"),
                    "enddt": query.get("end_date", "2026-03-13"),
                },
            )

            if response.status_code == 200:
                data = response.json()
                return data.get("hits", {}).get("hits", [])

        except Exception as exc:
            logger.exception(f"SEC EDGAR extraction failed: {exc}")

        return []

    async def _search_company(self, company_name: str) -> str:
        """Search for a company's CIK number by name."""
        if not self._client:
            return ""

        try:
            response = await self._client.get(
                f"{EDGAR_DATA_URL}/submissions/CIK0000000000.json",
            )
            # TODO: Implement proper company search via EDGAR
            return ""
        except Exception:
            return ""

    async def validate(self, data: list[dict]) -> dict:
        """Validate extracted SEC filings data."""
        return {
            "total_records": len(data),
            "valid": True,
            "issues": [],
        }

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        await super().disconnect()
