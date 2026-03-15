"""
HubSpot connector.

Extracts marketing metrics, lead funnel data, and campaign ROI
from HubSpot via REST API.

Authentication: HubSpot Private App Token (recommended) or API Key.
Required credentials keys:
  - access_token   HubSpot private app access token (Bearer)
  - company_name   Target company name (for context)

HubSpot API docs: https://developers.hubspot.com/docs/api/overview
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

import httpx

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

_BASE_URL = "https://api.hubapi.com"
_TIMEOUT = httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0)


class HubSpotConnector(BaseConnector):
    """Connector for HubSpot CRM and Marketing data via REST API."""

    system_name = "hubspot"
    category = "marketing"

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self._access_token: str = ""
        self._client: httpx.AsyncClient | None = None

    def _get_client(self) -> httpx.AsyncClient:
        if not self._client or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=_BASE_URL,
                headers={
                    "Authorization": f"Bearer {self._access_token}",
                    "Content-Type": "application/json",
                },
                timeout=_TIMEOUT,
            )
        return self._client

    async def authenticate(self, credentials: dict) -> AuthSession:
        self._access_token = credentials.get("access_token", "")
        if not self._access_token:
            logger.warning("HubSpot: no access_token in credentials")
        logger.info("HubSpot: access token stored")
        return AuthSession(self.system_name, AuthFlowType.API_KEY, {"configured": bool(self._access_token)})

    async def extract(self, query: dict) -> list[dict]:
        query_type = query.get("type", "")
        extractors = {
            "marketing_metrics": self._extract_marketing_metrics,
            "lead_funnel": self._extract_lead_funnel,
            "campaign_roi": self._extract_campaign_roi,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("HubSpot: unknown query type '%s'", query_type)
            return []
        try:
            return await extractor()
        except httpx.HTTPStatusError as exc:
            logger.warning("HubSpot[%s]: HTTP %s — %s", query_type, exc.response.status_code, exc.response.text[:200])
            return []
        except Exception as exc:
            logger.exception("HubSpot[%s]: unexpected error: %s", query_type, exc)
            return []

    async def _extract_marketing_metrics(self) -> list[dict]:
        """Extract contact lifecycle stage distribution and core marketing KPIs."""
        client = self._get_client()

        # Get contacts grouped by lifecycle stage
        stage_counts: dict[str, int] = {}
        for stage in ["subscriber", "lead", "marketingqualifiedlead", "salesqualifiedlead", "opportunity", "customer"]:
            resp = await client.post(
                "/crm/v3/objects/contacts/search",
                json={
                    "filterGroups": [{"filters": [{"propertyName": "lifecyclestage", "operator": "EQ", "value": stage}]}],
                    "properties": ["lifecyclestage"],
                    "limit": 1,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            stage_counts[stage] = data.get("total", 0)

        # Get total contacts
        resp = await client.post("/crm/v3/objects/contacts/search", json={"limit": 1})
        resp.raise_for_status()
        total_contacts = resp.json().get("total", 0)

        mql = stage_counts.get("marketingqualifiedlead", 0)
        sql = stage_counts.get("salesqualifiedlead", 0)
        customers = stage_counts.get("customer", 0)
        leads = stage_counts.get("lead", 0) + mql + sql

        return [{
            "metric": "contact_lifecycle_distribution",
            "as_of": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "total_contacts": total_contacts,
            "subscribers": stage_counts.get("subscriber", 0),
            "leads": leads,
            "mql": mql,
            "sql": sql,
            "opportunities": stage_counts.get("opportunity", 0),
            "customers": customers,
            "lead_to_mql_rate_pct": round(mql / leads * 100, 1) if leads else 0,
            "mql_to_sql_rate_pct": round(sql / mql * 100, 1) if mql else 0,
            "sql_to_customer_rate_pct": round(customers / sql * 100, 1) if sql else 0,
        }]

    async def _extract_lead_funnel(self) -> list[dict]:
        """Extract deal pipeline funnel — stages and deal counts/values."""
        client = self._get_client()

        # Get all deal pipelines
        resp = await client.get("/crm/v3/pipelines/deals")
        resp.raise_for_status()
        pipelines = resp.json().get("results", [])

        funnel_data = []
        for pipeline in pipelines[:3]:  # Top 3 pipelines
            pipeline_id = pipeline["id"]
            pipeline_label = pipeline.get("label", "Unknown")
            stages = pipeline.get("stages", [])

            for stage in stages:
                stage_id = stage["id"]
                stage_label = stage.get("label", "Unknown")
                stage_probability = stage.get("metadata", {}).get("probability", "0")

                # Count deals in this stage
                resp = await client.post(
                    "/crm/v3/objects/deals/search",
                    json={
                        "filterGroups": [{"filters": [
                            {"propertyName": "pipeline", "operator": "EQ", "value": pipeline_id},
                            {"propertyName": "dealstage", "operator": "EQ", "value": stage_id},
                        ]}],
                        "properties": ["amount", "dealstage", "closedate"],
                        "limit": 100,
                    },
                )
                resp.raise_for_status()
                stage_data = resp.json()
                deals = stage_data.get("results", [])
                total_value = sum(
                    float(d["properties"].get("amount") or 0)
                    for d in deals
                )

                funnel_data.append({
                    "pipeline": pipeline_label,
                    "stage": stage_label,
                    "deal_count": stage_data.get("total", 0),
                    "total_value_usd": round(total_value, 2),
                    "avg_deal_value_usd": round(total_value / len(deals), 2) if deals else 0,
                    "win_probability_pct": round(float(stage_probability) * 100, 1),
                })

        return funnel_data

    async def _extract_campaign_roi(self) -> list[dict]:
        """Extract email marketing campaign performance metrics."""
        client = self._get_client()

        # List email campaigns
        resp = await client.get(
            "/marketing/v3/campaigns",
            params={"limit": 25, "sort": "-updatedAt"},
        )
        if resp.status_code == 404:
            # Fallback: use marketing emails endpoint
            resp = await client.get("/marketing/v3/emails", params={"limit": 25})
            if resp.status_code != 200:
                logger.warning("HubSpot: marketing campaigns/emails endpoint unavailable (status=%s)", resp.status_code)
                return []
            emails = resp.json().get("results", [])
            return [
                {
                    "campaign": e.get("name", "Unknown"),
                    "type": e.get("type", "email"),
                    "status": e.get("publishDate", {}) and "published" or e.get("state", "unknown"),
                    "created_at": e.get("created", ""),
                    "updated_at": e.get("updatedAt", ""),
                }
                for e in emails
            ]

        resp.raise_for_status()
        campaigns = resp.json().get("results", [])

        results = []
        for campaign in campaigns:
            campaign_id = campaign.get("id")
            name = campaign.get("name", "Unknown")

            # Try to get campaign stats
            try:
                stats_resp = await client.get(f"/marketing/v3/campaigns/{campaign_id}/stats")
                stats = stats_resp.json() if stats_resp.status_code == 200 else {}
            except Exception:
                stats = {}

            results.append({
                "campaign": name,
                "campaign_id": campaign_id,
                "start_date": campaign.get("startDate", ""),
                "end_date": campaign.get("endDate", ""),
                "budget_usd": campaign.get("budget", {}).get("budgetAmount", 0),
                "currency": campaign.get("budget", {}).get("currency", "USD"),
                "contacts_enrolled": stats.get("contactsEnrolled", 0),
                "emails_sent": stats.get("emailsSent", 0),
                "open_rate_pct": stats.get("openRate", 0),
                "click_rate_pct": stats.get("clickRate", 0),
                "revenue_attributed_usd": stats.get("revenueAttribution", 0),
            })

        return results

    async def validate(self, data: list[dict]) -> dict:
        return {"total_records": len(data), "valid": True, "issues": []}

    async def disconnect(self) -> None:
        if self._client and not self._client.is_closed:
            await self._client.aclose()
        await super().disconnect()
