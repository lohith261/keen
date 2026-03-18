"""
Tegus expert call transcript integration.

Tegus (tegus.co) provides transcripts of expert calls — ex-employees and
industry experts interviewed about specific companies. PE firms pay $50K+/year
for access. KEEN fetches transcripts via the Tegus API and extracts:
  - Key themes and signals about the target company
  - Sentiment (positive / neutral / negative)
  - Specific insights about operations, culture, competitive position

Tegus API docs: https://tegus.co/api
Authentication: API Key (passed as Bearer token)

Required credentials (stored in KEEN vault under system_name="tegus"):
  - api_key   Tegus API key (from Account → API Access)
"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

TEGUS_API = "https://api.tegus.co/v1"


class TegusClient:
    """Client for the Tegus expert call transcript API."""

    system_name = "tegus"
    display_name = "Tegus"
    category = "expert_network"

    def __init__(self, api_key: str) -> None:
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

    # ── Search ────────────────────────────────────────────────────────────────

    async def search_transcripts(
        self,
        company_name: str,
        max_results: int = 20,
    ) -> list[dict[str, Any]]:
        """
        Search for transcripts about a company.

        Returns list of transcript metadata (without full text).
        Each item: {id, title, expert_name, expert_role, call_date, company_name, preview}
        """
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(
                f"{TEGUS_API}/transcripts",
                headers=self._headers(),
                params={
                    "q": company_name,
                    "company": company_name,
                    "limit": max_results,
                    "sort": "date_desc",
                },
            )
            resp.raise_for_status()
            body = resp.json()

        results = []
        for item in body.get("transcripts", body.get("data", [])):
            results.append({
                "id": item.get("id"),
                "external_id": f"tegus:{item.get('id')}",
                "title": item.get("title", "Expert Call Transcript"),
                "expert_name": item.get("expert", {}).get("name") if isinstance(item.get("expert"), dict) else item.get("expert_name"),
                "expert_role": item.get("expert", {}).get("role") if isinstance(item.get("expert"), dict) else item.get("expert_role"),
                "call_date": item.get("date") or item.get("call_date"),
                "company_name": company_name,
                "preview": item.get("excerpt") or item.get("preview", ""),
            })

        logger.info("Tegus: found %d transcripts for '%s'", len(results), company_name)
        return results

    async def get_transcript(self, transcript_id: str) -> dict[str, Any]:
        """
        Fetch the full text of a single transcript.

        Returns: {id, title, expert_name, expert_role, call_date, text, word_count}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(
                f"{TEGUS_API}/transcripts/{transcript_id}",
                headers=self._headers(),
            )
            resp.raise_for_status()
            item = resp.json()

        return {
            "id": item.get("id"),
            "external_id": f"tegus:{item.get('id')}",
            "title": item.get("title", "Expert Call Transcript"),
            "expert_name": item.get("expert", {}).get("name") if isinstance(item.get("expert"), dict) else item.get("expert_name"),
            "expert_role": item.get("expert", {}).get("role") if isinstance(item.get("expert"), dict) else item.get("expert_role"),
            "call_date": item.get("date") or item.get("call_date"),
            "text": item.get("transcript") or item.get("text", ""),
            "word_count": item.get("word_count"),
        }

    async def fetch_for_company(
        self, company_name: str, max_transcripts: int = 10
    ) -> list[dict[str, Any]]:
        """Search and fetch full text for the top N transcripts about a company."""
        summaries = await self.search_transcripts(company_name, max_results=max_transcripts)
        full_transcripts = []
        for s in summaries[:max_transcripts]:
            try:
                full = await self.get_transcript(s["id"])
                full_transcripts.append(full)
            except Exception as exc:
                logger.warning("Tegus: failed to fetch transcript %s — %s", s["id"], exc)
        return full_transcripts
