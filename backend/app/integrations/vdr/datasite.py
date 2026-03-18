"""
Datasite Virtual Data Room integration.

Uses the Datasite Partner API to list and download documents from a deal
data room without requiring the analyst to manually re-upload each file to KEEN.

Datasite Partner API docs: https://developers.datasite.com/
Authentication: OAuth 2.0 client credentials (partner_id + partner_secret)

Required credentials (stored in KEEN vault under system_name="datasite"):
  - partner_id       Datasite Partner API client ID
  - partner_secret   Datasite Partner API client secret
  - project_id       Datasite project (deal room) ID
  - folder_path      Folder path to ingest (default: "/" — entire room)

The connector fetches the directory listing and returns extracted metadata
for each document. Actual binary download is gated by file size
(max KEEN_VDR_MAX_MB env var, default 50 MB per file).
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

DATASITE_API = "https://api.datasite.com/v1"
MAX_FILE_MB = int(os.getenv("KEEN_VDR_MAX_MB", "50"))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


class DatasiteConnector:
    """Datasite Partner API client for VDR document ingestion."""

    system_name = "datasite"
    display_name = "Datasite VDR"
    category = "data_room"

    def __init__(self, credentials: dict[str, str]) -> None:
        self.partner_id = credentials["partner_id"]
        self.partner_secret = credentials["partner_secret"]
        self.project_id = credentials["project_id"]
        self.folder_path = credentials.get("folder_path", "/")
        self._token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Obtain an OAuth 2.0 access token via client credentials."""
        if self._token:
            return self._token
        resp = await client.post(
            f"{DATASITE_API}/oauth/token",
            data={
                "grant_type": "client_credentials",
                "client_id": self.partner_id,
                "client_secret": self.partner_secret,
                "scope": "documents:read projects:read",
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token  # type: ignore[return-value]

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ── Document listing ──────────────────────────────────────────────────────

    async def list_documents(self) -> list[dict[str, Any]]:
        """
        Return a flat list of all documents in the configured folder.

        Each item: {id, name, path, size_bytes, content_type, modified_at}
        """
        async with httpx.AsyncClient(timeout=30) as client:
            token = await self._get_token(client)
            headers = self._auth_headers(token)

            params: dict[str, Any] = {
                "project_id": self.project_id,
                "path": self.folder_path,
                "recursive": True,
                "page_size": 200,
            }
            docs: list[dict[str, Any]] = []
            page_token: str | None = None

            while True:
                if page_token:
                    params["page_token"] = page_token

                resp = await client.get(
                    f"{DATASITE_API}/documents",
                    params=params,
                    headers=headers,
                )
                resp.raise_for_status()
                body = resp.json()

                for item in body.get("items", []):
                    if item.get("type") == "file":
                        docs.append({
                            "id": item["id"],
                            "name": item["name"],
                            "path": item.get("path", "/"),
                            "size_bytes": item.get("size", 0),
                            "content_type": item.get("content_type", "application/octet-stream"),
                            "modified_at": item.get("modified_at"),
                        })

                page_token = body.get("next_page_token")
                if not page_token:
                    break

        logger.info("Datasite: found %d documents in project %s", len(docs), self.project_id)
        return docs

    async def download_document(self, document_id: str) -> bytes:
        """Download a single document by ID and return its raw bytes."""
        async with httpx.AsyncClient(timeout=120) as client:
            token = await self._get_token(client)
            resp = await client.get(
                f"{DATASITE_API}/documents/{document_id}/download",
                headers=self._auth_headers(token),
                follow_redirects=True,
            )
            resp.raise_for_status()

            if len(resp.content) > MAX_FILE_BYTES:
                raise ValueError(
                    f"File exceeds {MAX_FILE_MB} MB limit "
                    f"({len(resp.content) / (1024*1024):.1f} MB)"
                )
            return resp.content

    async def ingest(self) -> list[dict[str, Any]]:
        """
        List all documents and download + return those under the size limit.

        Returns list of {name, path, size_bytes, content_type, data (bytes)}.
        Silently skips files over the size limit or with download errors.
        """
        docs = await self.list_documents()
        results: list[dict[str, Any]] = []

        for doc in docs:
            if doc["size_bytes"] > MAX_FILE_BYTES:
                logger.info(
                    "Datasite: skipping %s — %.1f MB > limit",
                    doc["name"], doc["size_bytes"] / (1024 * 1024),
                )
                continue
            try:
                data = await self.download_document(doc["id"])
                results.append({**doc, "data": data})
            except Exception as exc:
                logger.warning("Datasite: failed to download %s — %s", doc["name"], exc)

        logger.info("Datasite: ingested %d/%d files", len(results), len(docs))
        return results
