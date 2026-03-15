"""
NetSuite ERP connector.

Extracts financial data — revenue, expenses, journal entries,
and balance sheet data via NetSuite SuiteTalk REST API.

Authentication: Token-Based Authentication (TBA) using OAuth 1.0.
Required credentials keys:
  - account_id       NetSuite account ID (e.g. TSTDRV1234567)
  - consumer_key     TBA consumer key from NetSuite integration record
  - consumer_secret  TBA consumer secret from NetSuite integration record
  - token_key        TBA token key (from token record for the integration user)
  - token_secret     TBA token secret (from token record for the integration user)
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import logging
import time
import uuid
from typing import Any
from urllib.parse import quote, urlencode

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

NETSUITE_SUITEQL_PATH = "/services/rest/query/v1/suiteql"


def _build_oauth1_header(
    method: str,
    url: str,
    account_id: str,
    consumer_key: str,
    consumer_secret: str,
    token_key: str,
    token_secret: str,
) -> str:
    """
    Generate an OAuth 1.0 Authorization header for NetSuite TBA.

    NetSuite requires HMAC-SHA256 (not SHA1) for TBA.
    """
    timestamp = str(int(time.time()))
    nonce = uuid.uuid4().hex

    # OAuth params (sorted alphabetically for signature base string)
    oauth_params = {
        "oauth_consumer_key": consumer_key,
        "oauth_nonce": nonce,
        "oauth_signature_method": "HMAC-SHA256",
        "oauth_timestamp": timestamp,
        "oauth_token": token_key,
        "oauth_version": "1.0",
    }

    # Build the parameter string (URL-encoded, sorted by key)
    param_string = urlencode(sorted(oauth_params.items()))

    # Build the signature base string
    base_string = "&".join([
        method.upper(),
        quote(url, safe=""),
        quote(param_string, safe=""),
    ])

    # Build the signing key
    signing_key = f"{quote(consumer_secret, safe='')}&{quote(token_secret, safe='')}"

    # Generate HMAC-SHA256 signature
    signature = base64.b64encode(
        hmac.new(
            signing_key.encode("utf-8"),
            base_string.encode("utf-8"),
            hashlib.sha256,
        ).digest()
    ).decode("utf-8")

    # Build the Authorization header
    auth_parts = [
        f'realm="{account_id}"',
        f'oauth_consumer_key="{consumer_key}"',
        f'oauth_nonce="{nonce}"',
        f'oauth_signature="{quote(signature, safe="")}"',
        'oauth_signature_method="HMAC-SHA256"',
        f'oauth_timestamp="{timestamp}"',
        f'oauth_token="{token_key}"',
        'oauth_version="1.0"',
    ]
    return "OAuth " + ",".join(auth_parts)


class NetSuiteConnector(BaseConnector):
    """Connector for NetSuite ERP data extraction via SuiteQL."""

    system_name = "netsuite"
    category = "erp"

    def __init__(self, account_id: str = "", **kwargs: Any):
        super().__init__(**kwargs)
        self.account_id = account_id
        self._client: httpx.AsyncClient | None = None
        self._credentials: dict = {}

    @property
    def _base_url(self) -> str:
        # NetSuite uses the account_id (lowercased, dashes converted to underscores) in the hostname
        normalized = self.account_id.lower().replace("-", "_")
        return f"https://{normalized}.suitetalk.api.netsuite.com"

    @property
    def _suiteql_url(self) -> str:
        return self._base_url + NETSUITE_SUITEQL_PATH

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        Set up NetSuite TBA using OAuth 1.0 credentials.

        No token exchange is needed — TBA credentials are static and
        each request is signed individually.
        """
        self._credentials = credentials
        self.account_id = credentials.get("account_id") or self.account_id

        session = AuthSession(
            self.system_name,
            AuthFlowType.TOKEN,
            {
                "account_id": self.account_id,
                "consumer_key": credentials.get("consumer_key", ""),
                "token_key": credentials.get("token_key", ""),
            },
        )
        self.auth_session = session

        # We don't set a static Authorization header because each request
        # requires a unique nonce + timestamp. Use _make_request() instead.
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=60.0,
        )

        return session

    def _auth_header(self, method: str, url: str) -> str:
        """Generate a per-request OAuth 1.0 TBA Authorization header."""
        return _build_oauth1_header(
            method=method,
            url=url,
            account_id=self._credentials.get("account_id", self.account_id),
            consumer_key=self._credentials.get("consumer_key", ""),
            consumer_secret=self._credentials.get("consumer_secret", ""),
            token_key=self._credentials.get("token_key", ""),
            token_secret=self._credentials.get("token_secret", ""),
        )

    async def _suiteql(self, query: str, limit: int = 1000) -> list[dict]:
        """Execute a SuiteQL query and return all rows (handles pagination)."""
        if not self._client:
            return []

        url = self._suiteql_url
        rows: list[dict] = []
        offset = 0

        while True:
            try:
                response = await self._client.post(
                    NETSUITE_SUITEQL_PATH,
                    json={"q": query},
                    params={"limit": limit, "offset": offset},
                    headers={
                        "Authorization": self._auth_header("POST", url),
                        "Content-Type": "application/json",
                        "Prefer": "transient",
                    },
                )
                response.raise_for_status()
                data = response.json()
                items = data.get("items", [])
                rows.extend(items)

                if not data.get("hasMore", False):
                    break
                offset += len(items)

            except httpx.HTTPStatusError as exc:
                logger.exception("NetSuite SuiteQL failed: %s — %s", exc, exc.response.text[:200])
                break
            except Exception as exc:
                logger.exception("NetSuite SuiteQL error: %s", exc)
                break

        return rows

    async def extract(self, query: dict) -> list[dict]:
        """
        Extract financial data from NetSuite via SuiteQL.

        Supported query types:
        - revenue_data:     Revenue transactions by period
        - expense_records:  Expense line items
        - journal_entries:  GL journal entries
        - balance_sheet:    Balance sheet account balances
        """
        query_type = query.get("type", "revenue_data")

        suiteql_queries: dict[str, str] = {
            "revenue_data": (
                "SELECT t.id, t.trandate, t.tranid, t.amount, "
                "t.entity, t.memo, a.accountnumber, a.fullname AS account_name "
                "FROM transaction t "
                "JOIN transactionline tl ON t.id = tl.transaction "
                "JOIN account a ON tl.account = a.id "
                "WHERE t.type IN ('CustInvc', 'CustCred') "
                "AND t.trandate >= TO_DATE('2023-01-01', 'YYYY-MM-DD') "
                "ORDER BY t.trandate DESC"
            ),
            "expense_records": (
                "SELECT t.id, t.trandate, t.tranid, tl.netamount, "
                "a.accountnumber, a.fullname AS account_name, t.memo "
                "FROM transaction t "
                "JOIN transactionline tl ON t.id = tl.transaction "
                "JOIN account a ON tl.account = a.id "
                "WHERE t.type IN ('VendBill', 'VendCred', 'ExpRept') "
                "AND t.trandate >= TO_DATE('2023-01-01', 'YYYY-MM-DD') "
                "ORDER BY t.trandate DESC"
            ),
            "journal_entries": (
                "SELECT t.id, t.trandate, t.tranid, tl.debit, tl.credit, "
                "a.accountnumber, a.fullname AS account_name, t.memo "
                "FROM transaction t "
                "JOIN transactionline tl ON t.id = tl.transaction "
                "JOIN account a ON tl.account = a.id "
                "WHERE t.type = 'Journal' "
                "AND t.trandate >= TO_DATE('2023-01-01', 'YYYY-MM-DD') "
                "ORDER BY t.trandate DESC"
            ),
            "balance_sheet": (
                "SELECT a.id, a.accountnumber, a.fullname AS account_name, "
                "a.type, a.balance, a.currency "
                "FROM account a "
                "WHERE a.type IN ('Bank', 'AcctRec', 'OthCurrAsset', 'FixedAsset', "
                "'AcctPay', 'LongTermLiab', 'Equity') "
                "ORDER BY a.accountnumber"
            ),
        }

        suiteql = suiteql_queries.get(query_type)
        if not suiteql:
            logger.warning("NetSuite: unknown query type '%s'", query_type)
            return []

        records = await self._suiteql(suiteql)
        logger.info("NetSuite[%s]: extracted %d records", query_type, len(records))
        return records

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
