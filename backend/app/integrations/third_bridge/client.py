"""
Third Bridge expert call transcript integration.

Third Bridge (thirdbridge.com) provides primary research: expert interview
transcripts and forum posts from industry practitioners. Like Tegus, PE
firms pay $50K+/year for access.

Third Bridge API docs: https://api.thirdbridge.com/docs
Authentication: OAuth 2.0 client credentials (client_id + client_secret)

Required credentials (stored in KEEN vault under system_name="third_bridge"):
  - client_id       Third Bridge API client ID
  - client_secret   Third Bridge API client secret
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

THIRD_BRIDGE_API = "https://api.thirdbridge.com/v2"
TOKEN_URL = "https://auth.thirdbridge.com/oauth/token"


class ThirdBridgeClient:
    """Client for the Third Bridge expert research API."""

    system_name = "third_bridge"
    display_name = "Third Bridge"
    category = "expert_network"

    def __init__(self, client_id: str, client_secret: str) -> None:
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        if self._token:
            return self._token
        resp = await client.post(
            TOKEN_URL,
            json={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "audience": THIRD_BRIDGE_API,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token  # type: ignore[return-value]

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_interviews(
        self,
        company_name: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for Third Bridge Forum posts and interview transcripts.

        Returns: list of {id, title, expert_name, expert_role, call_date, preview}
        """
        async with httpx.AsyncClient(timeout=20) as client:
            token = await self._get_token(client)
            resp = await client.get(
                f"{THIRD_BRIDGE_API}/interviews",
                headers=self._auth_headers(token),
                params={
                    "query": company_name,
                    "company_name": company_name,
                    "limit": max_results,
                    "sort": "-date",
                },
            )
            resp.raise_for_status()
            body = resp.json()

        results = []
        for item in body.get("data", body.get("interviews", [])):
            results.append({
                "id": item.get("id"),
                "external_id": f"third_bridge:{item.get('id')}",
                "title": item.get("title", "Third Bridge Interview"),
                "expert_name": item.get("expert_name") or (
                    item.get("expert", {}).get("name")
                    if isinstance(item.get("expert"), dict) else None
                ),
                "expert_role": item.get("expert_role") or (
                    item.get("expert", {}).get("role")
                    if isinstance(item.get("expert"), dict) else None
                ),
                "call_date": item.get("date") or item.get("interview_date"),
                "company_name": company_name,
                "preview": item.get("summary") or item.get("excerpt", ""),
            })

        logger.info("Third Bridge: found %d interviews for '%s'", len(results), company_name)
        return results

    async def get_interview(self, interview_id: str) -> dict[str, Any]:
        """Fetch full transcript for a single interview."""
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._get_token(client)
            resp = await client.get(
                f"{THIRD_BRIDGE_API}/interviews/{interview_id}",
                headers=self._auth_headers(token),
            )
            resp.raise_for_status()
            item = resp.json()

        return {
            "id": item.get("id"),
            "external_id": f"third_bridge:{item.get('id')}",
            "title": item.get("title", "Third Bridge Interview"),
            "expert_name": item.get("expert_name"),
            "expert_role": item.get("expert_role"),
            "call_date": item.get("date") or item.get("interview_date"),
            "text": item.get("transcript") or item.get("content", ""),
            "word_count": item.get("word_count"),
        }

    async def fetch_for_company(
        self, company_name: str, max_interviews: int = 10
    ) -> list[dict[str, Any]]:
        """Search and fetch full text for the top N interviews about a company."""
        summaries = await self.search_interviews(company_name, max_results=max_interviews)
        full_interviews = []
        for s in summaries[:max_interviews]:
            try:
                full = await self.get_interview(s["id"])
                full_interviews.append(full)
            except Exception as exc:
                logger.warning(
                    "Third Bridge: failed to fetch interview %s — %s", s["id"], exc
                )
        return full_interviews
