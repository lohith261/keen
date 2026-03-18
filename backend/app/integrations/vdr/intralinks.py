"""
Intralinks Virtual Data Room integration.

Uses the Intralinks REST API v2 to list and download documents from a
deal exchange (data room) and ingest them into KEEN's analysis pipeline.

Intralinks API docs: https://developers.intralinks.com/
Authentication: OAuth 2.0 with username + password (resource owner password credentials)
  POST /v2/oauth2/token with grant_type=password

Required credentials (stored in KEEN vault under system_name="intralinks"):
  - username         Intralinks login email
  - password         Intralinks login password
  - workspace_id     Exchange / workspace ID (from the deal room URL)
  - folder_id        Root folder ID to ingest (optional — defaults to root)
"""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

logger = logging.getLogger(__name__)

INTRALINKS_API = "https://api.intralinks.com/v2"
MAX_FILE_MB = int(os.getenv("KEEN_VDR_MAX_MB", "50"))
MAX_FILE_BYTES = MAX_FILE_MB * 1024 * 1024


class IntralinksConnector:
    """Intralinks REST API client for VDR document ingestion."""

    system_name = "intralinks"
    display_name = "Intralinks VDR"
    category = "data_room"

    def __init__(self, credentials: dict[str, str]) -> None:
        self.username = credentials["username"]
        self.password = credentials["password"]
        self.workspace_id = credentials["workspace_id"]
        self.folder_id = credentials.get("folder_id", "root")
        self._token: str | None = None

    # ── Auth ──────────────────────────────────────────────────────────────────

    async def _get_token(self, client: httpx.AsyncClient) -> str:
        """Obtain an OAuth 2.0 access token via resource owner password."""
        if self._token:
            return self._token
        resp = await client.post(
            f"{INTRALINKS_API}/oauth2/token",
            data={
                "grant_type": "password",
                "username": self.username,
                "password": self.password,
            },
            headers={"Accept": "application/json"},
        )
        resp.raise_for_status()
        self._token = resp.json()["access_token"]
        return self._token  # type: ignore[return-value]

    def _auth_headers(self, token: str) -> dict[str, str]:
        return {"Authorization": f"Bearer {token}", "Accept": "application/json"}

    # ── Document listing ──────────────────────────────────────────────────────

    async def list_folder(
        self, client: httpx.AsyncClient, token: str, folder_id: str
    ) -> list[dict[str, Any]]:
        """Recursively list documents in a folder."""
        resp = await client.get(
            f"{INTRALINKS_API}/workspaces/{self.workspace_id}/folders/{folder_id}/documents",
            headers=self._auth_headers(token),
            params={"max": 500},
        )
        resp.raise_for_status()
        body = resp.json()

        docs: list[dict[str, Any]] = []
        for item in body.get("document", []):
            docs.append({
                "id": item["id"],
                "name": item.get("name", "unnamed"),
                "path": item.get("groupFullPath", "/"),
                "size_bytes": item.get("fileSize", 0),
                "content_type": item.get("fileType", "application/octet-stream"),
                "modified_at": item.get("modifiedDate"),
            })

        # Recurse into sub-folders
        sub_resp = await client.get(
            f"{INTRALINKS_API}/workspaces/{self.workspace_id}/folders/{folder_id}/subfolders",
            headers=self._auth_headers(token),
        )
        if sub_resp.is_success:
            for sub in sub_resp.json().get("folder", []):
                docs.extend(await self.list_folder(client, token, sub["id"]))

        return docs

    async def list_documents(self) -> list[dict[str, Any]]:
        """Return all documents in the workspace under the configured folder."""
        async with httpx.AsyncClient(timeout=60) as client:
            token = await self._get_token(client)
            docs = await self.list_folder(client, token, self.folder_id)

        logger.info(
            "Intralinks: found %d documents in workspace %s", len(docs), self.workspace_id
        )
        return docs

    async def download_document(self, document_id: str) -> bytes:
        """Download a document by ID."""
        async with httpx.AsyncClient(timeout=120) as client:
            token = await self._get_token(client)
            resp = await client.get(
                f"{INTRALINKS_API}/workspaces/{self.workspace_id}/documents/{document_id}/download",
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
        """List and download all documents under the size limit."""
        docs = await self.list_documents()
        results: list[dict[str, Any]] = []

        for doc in docs:
            if doc["size_bytes"] > MAX_FILE_BYTES:
                logger.info(
                    "Intralinks: skipping %s — %.1f MB > limit",
                    doc["name"], doc["size_bytes"] / (1024 * 1024),
                )
                continue
            try:
                data = await self.download_document(doc["id"])
                results.append({**doc, "data": data})
            except Exception as exc:
                logger.warning("Intralinks: failed to download %s — %s", doc["name"], exc)

        logger.info("Intralinks: ingested %d/%d files", len(results), len(docs))
        return results
