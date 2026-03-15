"""
Salesforce CRM connector.

Extracts pipeline data, deal history, contact records, and activity logs
via Salesforce REST API (SOQL queries).

Authentication: OAuth 2.0 with refresh-token grant.
Required credentials keys:
  - client_id        Salesforce Connected App consumer key
  - client_secret    Salesforce Connected App consumer secret
  - refresh_token    Long-lived refresh token obtained during initial OAuth flow
  - instance_url     e.g. https://mycompany.my.salesforce.com
  - access_token     (optional) pre-existing access token; refreshed automatically
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

SALESFORCE_TOKEN_URL = "https://login.salesforce.com/services/oauth2/token"
SALESFORCE_API_VERSION = "v59.0"


class SalesforceConnector(BaseConnector):
    """Connector for Salesforce CRM data extraction."""

    system_name = "salesforce"
    category = "crm"

    def __init__(self, instance_url: str = "", **kwargs: Any):
        super().__init__(**kwargs)
        self.instance_url = instance_url
        self._client: httpx.AsyncClient | None = None
        self._credentials: dict = {}

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        Authenticate to Salesforce via OAuth 2.0.

        Tries to use an existing access_token first. If refresh_token is
        provided, performs the token refresh grant to get a fresh token.
        """
        self._credentials = credentials
        instance_url = credentials.get("instance_url") or self.instance_url

        access_token = credentials.get("access_token", "")
        refresh_token = credentials.get("refresh_token", "")
        client_id = credentials.get("client_id", "")
        client_secret = credentials.get("client_secret", "")

        # Attempt token refresh if refresh_token is available
        if refresh_token and client_id:
            try:
                access_token, instance_url = await self._refresh_access_token(
                    client_id=client_id,
                    client_secret=client_secret,
                    refresh_token=refresh_token,
                )
                logger.info("Salesforce: refreshed access token via refresh_token grant")
            except Exception as exc:
                logger.warning("Salesforce token refresh failed: %s — using stored token", exc)

        self.instance_url = instance_url

        session = AuthSession(
            self.system_name,
            AuthFlowType.OAUTH,
            {
                "access_token": access_token,
                "instance_url": instance_url,
            },
        )
        self.auth_session = session

        self._client = httpx.AsyncClient(
            base_url=instance_url,
            headers={"Authorization": f"Bearer {access_token}"},
            timeout=30.0,
        )

        return session

    async def _refresh_access_token(
        self,
        client_id: str,
        client_secret: str,
        refresh_token: str,
    ) -> tuple[str, str]:
        """Exchange a refresh token for a new access token. Returns (access_token, instance_url)."""
        async with httpx.AsyncClient(timeout=15.0) as client:
            response = await client.post(
                SALESFORCE_TOKEN_URL,
                data={
                    "grant_type": "refresh_token",
                    "client_id": client_id,
                    "client_secret": client_secret,
                    "refresh_token": refresh_token,
                },
            )
            response.raise_for_status()
            payload = response.json()
            return payload["access_token"], payload["instance_url"]

    async def extract(self, query: dict) -> list[dict]:
        """
        Extract data from Salesforce using SOQL queries.

        Supported query types:
        - pipeline_data:    Current open opportunities
        - deal_history:     Closed-won deals (last 12 months)
        - contact_records:  Key CRM contacts
        - activity_logs:    Recent tasks (last 90 days)
        """
        if not self._client:
            logger.warning("Salesforce: not authenticated, call authenticate() first")
            return []

        query_type = query.get("type", "pipeline_data")

        soql_queries: dict[str, str] = {
            "pipeline_data": (
                "SELECT Id, Name, Amount, StageName, CloseDate, Probability, "
                "Account.Name, Owner.Name "
                "FROM Opportunity WHERE IsClosed = false "
                "ORDER BY Amount DESC NULLS LAST LIMIT 500"
            ),
            "deal_history": (
                "SELECT Id, Name, Amount, CloseDate, StageName, "
                "Account.Name, Owner.Name "
                "FROM Opportunity WHERE IsWon = true "
                "AND CloseDate = LAST_N_MONTHS:12 "
                "ORDER BY CloseDate DESC LIMIT 500"
            ),
            "contact_records": (
                "SELECT Id, Name, Email, Title, Phone, Account.Name "
                "FROM Contact "
                "ORDER BY CreatedDate DESC LIMIT 1000"
            ),
            "activity_logs": (
                "SELECT Id, Subject, ActivityDate, Status, Priority, "
                "Owner.Name, Who.Name "
                "FROM Task WHERE ActivityDate = LAST_N_DAYS:90 "
                "ORDER BY ActivityDate DESC LIMIT 500"
            ),
        }

        soql = soql_queries.get(query_type)
        if not soql:
            logger.warning("Salesforce: unknown query type '%s'", query_type)
            return []

        try:
            response = await self._client.get(
                f"/services/data/{SALESFORCE_API_VERSION}/query",
                params={"q": soql},
            )
            response.raise_for_status()
            data = response.json()
            records = data.get("records", [])

            # Handle pagination (nextRecordsUrl)
            next_url = data.get("nextRecordsUrl")
            while next_url:
                page = await self._client.get(next_url)
                page.raise_for_status()
                page_data = page.json()
                records.extend(page_data.get("records", []))
                next_url = page_data.get("nextRecordsUrl")

            logger.info("Salesforce[%s]: extracted %d records", query_type, len(records))
            return records

        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 401:
                logger.warning("Salesforce: 401 Unauthorized — token may be expired")
            else:
                logger.exception("Salesforce SOQL failed [%s]: %s", query_type, exc)
            return []
        except Exception as exc:
            logger.exception("Salesforce extraction error [%s]: %s", query_type, exc)
            return []

    async def validate(self, data: list[dict]) -> dict:
        """Validate extracted Salesforce data."""
        issues = []
        for record in data:
            if "Id" not in record:
                issues.append("Record missing 'Id' field")
                break
        return {
            "total_records": len(data),
            "valid": len(issues) == 0,
            "issues": issues,
        }

    async def disconnect(self) -> None:
        """Close the HTTP client."""
        if self._client:
            await self._client.aclose()
        await super().disconnect()
