"""
SEC EDGAR connector.

Extracts public filing data — 10-K, 10-Q, proxy statements,
and insider transactions from the SEC EDGAR XBRL API.

No authentication required — SEC EDGAR is a public API.
SEC requires a descriptive User-Agent string with contact info.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

# SEC EDGAR requires a User-Agent with contact info per their guidelines
EDGAR_USER_AGENT = "KEEN/0.1.0 contact@keenai.com"

# API endpoints
EDGAR_SEARCH_URL = "https://efts.sec.gov/LATEST/search-index"
EDGAR_DATA_URL = "https://data.sec.gov"
EDGAR_SUBMISSIONS_URL = "https://data.sec.gov/submissions"


class SECEdgarConnector(BaseConnector):
    """Connector for SEC EDGAR public filings data."""

    system_name = "sec_edgar"
    category = "regulatory"

    def __init__(self, **kwargs: Any):
        super().__init__(**kwargs)
        self._client: httpx.AsyncClient | None = None
        self._cik_cache: dict[str, str] = {}

    async def authenticate(self, credentials: dict) -> AuthSession:
        """
        SEC EDGAR is public — no authentication needed.
        Just set up the HTTP client with the required User-Agent header.
        """
        session = AuthSession(self.system_name, AuthFlowType.PUBLIC)
        self.auth_session = session

        self._client = httpx.AsyncClient(
            headers={
                "User-Agent": EDGAR_USER_AGENT,
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
            timeout=30.0,
            follow_redirects=True,
        )

        return session

    async def extract(self, query: dict) -> list[dict]:
        """
        Extract filing data from SEC EDGAR.

        Supported query types:
        - 10k_filings:          Annual reports (10-K)
        - 10q_filings:          Quarterly reports (10-Q)
        - insider_transactions: Form 4 filings
        - proxy_statements:     DEF 14A proxy filings
        """
        if not self._client:
            logger.warning("SEC EDGAR: not authenticated, call authenticate() first")
            return []

        query_type = query.get("type", "10k_filings")
        company_name = query.get("company_name", "")
        company_cik = query.get("cik", "")

        # Look up CIK if not provided
        if not company_cik and company_name:
            company_cik = await self._search_company(company_name)

        if not company_cik:
            logger.warning("SEC EDGAR: could not resolve CIK for '%s'", company_name)
            return []

        form_types = {
            "10k_filings": "10-K",
            "10q_filings": "10-Q",
            "insider_transactions": "4",
            "proxy_statements": "DEF 14A",
        }

        form_type = form_types.get(query_type, "10-K")

        # Fetch filings via the submissions API (most reliable)
        return await self._fetch_filings_by_cik(
            cik=company_cik,
            form_type=form_type,
            query_type=query_type,
            start_date=query.get("start_date", "2022-01-01"),
            end_date=query.get("end_date", "2026-12-31"),
        )

    async def _search_company(self, company_name: str) -> str:
        """
        Look up a company's CIK by name using the EDGAR full-text search API.

        Returns the CIK as a zero-padded 10-digit string, or empty string if not found.
        """
        if company_name in self._cik_cache:
            return self._cik_cache[company_name]

        if not self._client:
            return ""

        try:
            # Use EDGAR full-text search — returns entity_id (the CIK) in results
            response = await self._client.get(
                EDGAR_SEARCH_URL,
                params={
                    "q": f'"{company_name}"',
                    "forms": "10-K",
                    "dateRange": "custom",
                    "startdt": "2015-01-01",
                    "enddt": "2026-12-31",
                },
            )
            response.raise_for_status()
            data = response.json()
            hits = data.get("hits", {}).get("hits", [])

            for hit in hits:
                source = hit.get("_source", {})
                # entity_id is the CIK (may be returned as int or string)
                entity_id = source.get("entity_id") or source.get("cik", "")
                display_names = source.get("display_names", [])

                if entity_id:
                    # Normalize company_name for fuzzy matching
                    search_lower = company_name.lower().replace(",", "").replace(".", "")
                    for display_name in display_names:
                        display_lower = display_name.lower().replace(",", "").replace(".", "")
                        if search_lower in display_lower or display_lower in search_lower:
                            cik = str(entity_id).zfill(10)
                            self._cik_cache[company_name] = cik
                            logger.info(
                                "SEC EDGAR: resolved '%s' → CIK %s (%s)",
                                company_name, cik, display_name,
                            )
                            return cik

            # Fallback: use the first result's entity_id if any hits exist
            if hits:
                entity_id = hits[0].get("_source", {}).get("entity_id", "")
                if entity_id:
                    cik = str(entity_id).zfill(10)
                    self._cik_cache[company_name] = cik
                    logger.info(
                        "SEC EDGAR: resolved '%s' → CIK %s (fallback first hit)",
                        company_name, cik,
                    )
                    return cik

        except Exception as exc:
            logger.exception("SEC EDGAR company search failed for '%s': %s", company_name, exc)

        logger.warning("SEC EDGAR: no CIK found for '%s'", company_name)
        return ""

    async def _fetch_filings_by_cik(
        self,
        cik: str,
        form_type: str,
        query_type: str,
        start_date: str,
        end_date: str,
    ) -> list[dict]:
        """
        Fetch recent filings for a CIK from the submissions API.

        The submissions API returns the full filing history; we filter by form type
        and date range.
        """
        if not self._client:
            return []

        # CIK must be zero-padded to 10 digits for the submissions URL
        padded_cik = cik.lstrip("0").zfill(10) if cik else cik
        url = f"{EDGAR_SUBMISSIONS_URL}/CIK{padded_cik}.json"

        try:
            response = await self._client.get(url)
            response.raise_for_status()
            data = response.json()

            company_name = data.get("name", "")
            filings = data.get("filings", {}).get("recent", {})

            if not filings:
                return []

            # Zip the parallel arrays into records
            accession_numbers = filings.get("accessionNumber", [])
            filing_dates = filings.get("filingDate", [])
            form_types = filings.get("form", [])
            primary_documents = filings.get("primaryDocument", [])
            descriptions = filings.get("primaryDocDescription", [])

            records = []
            for i, acc_num in enumerate(accession_numbers):
                f_type = form_types[i] if i < len(form_types) else ""
                f_date = filing_dates[i] if i < len(filing_dates) else ""

                # Filter by form type
                if f_type != form_type:
                    continue

                # Filter by date range
                if f_date < start_date or f_date > end_date:
                    continue

                # Build the filing URL
                acc_url = acc_num.replace("-", "")
                filing_url = (
                    f"https://www.sec.gov/Archives/edgar/data/"
                    f"{cik.lstrip('0')}/{acc_url}/"
                    f"{primary_documents[i] if i < len(primary_documents) else ''}"
                )

                records.append({
                    "cik": padded_cik,
                    "company_name": company_name,
                    "accession_number": acc_num,
                    "form_type": f_type,
                    "filing_date": f_date,
                    "description": descriptions[i] if i < len(descriptions) else "",
                    "filing_url": filing_url,
                })

            logger.info(
                "SEC EDGAR[%s]: found %d %s filings for CIK %s (%s)",
                query_type, len(records), form_type, padded_cik, company_name,
            )
            return records

        except httpx.HTTPStatusError as exc:
            logger.exception("SEC EDGAR submissions fetch failed for CIK %s: %s", cik, exc)
            return []
        except Exception as exc:
            logger.exception("SEC EDGAR extraction error for CIK %s: %s", cik, exc)
            return []

    async def validate(self, data: list[dict]) -> dict:
        """Validate extracted SEC filings data."""
        issues = []
        for record in data:
            if "accession_number" not in record:
                issues.append("Record missing 'accession_number' field")
                break
        return {
            "total_records": len(data),
            "valid": len(issues) == 0,
            "issues": issues,
        }

    async def disconnect(self) -> None:
        if self._client:
            await self._client.aclose()
        await super().disconnect()
