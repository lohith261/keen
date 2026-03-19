"""
Crunchbase connector.

Extracts funding history, acquisitions, and key people data
from Crunchbase via REST API.

Authentication: Crunchbase API v4 — API key.
Required credentials keys:
  - api_key        Crunchbase API user key
  - company_name   Target company name (used to look up the organization permalink)

Crunchbase API docs: https://data.crunchbase.com/docs/using-the-api
"""

from __future__ import annotations

import logging
import re
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.crunchbase.com/api/v4"
_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)


def _slugify(name: str) -> str:
    """Convert company name to Crunchbase-style permalink."""
    slug = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", slug)
    return slug.strip("-")


class CrunchbaseConnector(BaseConnector):
    """Connector for Crunchbase organization data via REST API."""

    system_name = "crunchbase"
    category = "intelligence"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._api_key: str = ""
        self._company_name: str = ""
        self._permalink: str = ""

    async def authenticate(self, credentials: dict) -> AuthSession:
        self._api_key = credentials.get("api_key", "")
        self._company_name = credentials.get("company_name", "")
        self._permalink = credentials.get("permalink", "") or _slugify(self._company_name)

        if not self._api_key:
            logger.warning("Crunchbase: no api_key in credentials")

        logger.info(
            "Crunchbase: API key stored, will look up permalink='%s'",
            self._permalink,
        )
        return AuthSession(
            self.system_name, AuthFlowType.API_KEY, {"configured": bool(self._api_key)}
        )

    def _params(self, extra: dict | None = None) -> dict:
        p = {"user_key": self._api_key}
        if extra:
            p.update(extra)
        return p

    async def _resolve_permalink(self, client: httpx.AsyncClient) -> str:
        """Search for the company and return its Crunchbase permalink."""
        resp = await client.post(
            f"{_BASE_URL}/searches/organizations",
            params=self._params(),
            json={
                "field_ids": ["identifier", "short_description"],
                "predicate": {
                    "field_id": "identifier",
                    "operator_id": "contains",
                    "values": [self._company_name],
                },
                "limit": 5,
            },
        )
        resp.raise_for_status()
        entities = resp.json().get("entities", [])
        if entities:
            return entities[0].get("identifier", {}).get("permalink", self._permalink)
        return self._permalink

    async def extract(self, query: dict) -> list[dict]:
        query_type = query.get("type", "")
        company_name = query.get("company_name") or self._company_name

        extractors = {
            "funding_history": self._extract_funding_history,
            "acquisitions": self._extract_acquisitions,
            "key_people": self._extract_key_people,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("Crunchbase: unknown query type '%s'", query_type)
            return []

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            try:
                # Resolve the permalink first
                self._permalink = await self._resolve_permalink(client)
                return await extractor(client)
            except httpx.HTTPStatusError as exc:
                logger.warning(
                    "Crunchbase[%s]: HTTP %s — %s",
                    query_type, exc.response.status_code, exc.response.text[:200],
                )
                return []
            except Exception as exc:
                logger.exception("Crunchbase[%s]: unexpected error: %s", query_type, exc)
                return []

    async def _extract_funding_history(self, client: httpx.AsyncClient) -> list[dict]:
        """Extract all funding rounds for the target company."""
        resp = await client.get(
            f"{_BASE_URL}/entities/organizations/{self._permalink}",
            params=self._params({
                "field_ids": "funding_rounds",
                "card_ids": "funding_rounds",
            }),
        )
        resp.raise_for_status()
        org_data = resp.json()

        rounds = (
            org_data.get("cards", {})
            .get("funding_rounds", [])
        )

        results = []
        for r in rounds:
            props = r.get("properties", r)
            results.append({
                "round_name": props.get("investment_type", ""),
                "series": props.get("series", ""),
                "announced_on": props.get("announced_on", {}).get("value", "") if isinstance(props.get("announced_on"), dict) else props.get("announced_on", ""),
                "raised_amount_usd": props.get("raised_amount_usd", 0),
                "pre_money_valuation_usd": props.get("pre_money_valuation_usd", 0),
                "lead_investors": [
                    inv.get("identifier", {}).get("value", "")
                    for inv in props.get("lead_investors", [])
                ],
                "investor_count": props.get("num_investors", 0),
            })

        logger.info("Crunchbase: fetched %d funding rounds", len(results))
        return results

    async def _extract_acquisitions(self, client: httpx.AsyncClient) -> list[dict]:
        """Extract acquisitions made by or of the target company."""
        resp = await client.get(
            f"{_BASE_URL}/entities/organizations/{self._permalink}",
            params=self._params({
                "field_ids": "num_acquisitions,acquired_by_identifier,ipo_status",
                "card_ids": "acquiree_acquisitions",
            }),
        )
        resp.raise_for_status()
        org_data = resp.json()

        acquisitions = (
            org_data.get("cards", {})
            .get("acquiree_acquisitions", [])
        )

        # Also check if company was acquired
        props = org_data.get("properties", {})
        acquired_by = props.get("acquired_by_identifier", {})
        results = []

        if acquired_by:
            results.append({
                "type": "acquired_by",
                "acquirer": acquired_by.get("value", ""),
                "acquirer_permalink": acquired_by.get("permalink", ""),
                "announced_on": props.get("acquired_on", {}).get("value", "") if isinstance(props.get("acquired_on"), dict) else "",
                "price_usd": props.get("acquisition_price_usd", 0),
            })

        for acq in acquisitions:
            ap = acq.get("properties", acq)
            results.append({
                "type": "acquiree",
                "target": ap.get("acquiree_identifier", {}).get("value", ""),
                "target_permalink": ap.get("acquiree_identifier", {}).get("permalink", ""),
                "announced_on": ap.get("announced_on", {}).get("value", "") if isinstance(ap.get("announced_on"), dict) else ap.get("announced_on", ""),
                "price_usd": ap.get("price_usd", 0),
                "acquisition_type": ap.get("acquisition_type", ""),
                "acquisition_status": ap.get("acquisition_status", ""),
            })

        logger.info("Crunchbase: fetched %d acquisition records", len(results))
        return results

    async def _extract_key_people(self, client: httpx.AsyncClient) -> list[dict]:
        """Extract founders, board members, and key executives."""
        resp = await client.get(
            f"{_BASE_URL}/entities/organizations/{self._permalink}",
            params=self._params({
                "field_ids": "num_employees_enum,founder_identifiers",
                "card_ids": "current_team",
            }),
        )
        resp.raise_for_status()
        org_data = resp.json()

        team = org_data.get("cards", {}).get("current_team", [])

        results = []
        for member in team:
            mp = member.get("properties", member)
            person = mp.get("person_identifier", {})
            results.append({
                "name": person.get("value", ""),
                "permalink": person.get("permalink", ""),
                "title": mp.get("title", ""),
                "started_on": mp.get("started_on", {}).get("value", "") if isinstance(mp.get("started_on"), dict) else mp.get("started_on", ""),
                "is_primary_job": mp.get("is_primary_job", False),
            })

        # Also get founders
        founders = org_data.get("properties", {}).get("founder_identifiers", [])
        founder_names = {f.get("value", "") for f in founders}
        for r in results:
            r["is_founder"] = r["name"] in founder_names

        logger.info("Crunchbase: fetched %d team members", len(results))
        return results

    async def validate(self, data: list[dict]) -> dict:
        return {"total_records": len(data), "valid": True, "issues": []}

    async def disconnect(self) -> None:
        await super().disconnect()
