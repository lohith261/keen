"""
SharePoint distribution connector.

Uploads KEEN due diligence reports to a SharePoint document library
via Microsoft Graph API using application-level client credentials.

Configuration (engagement config keys):
  sharepoint_tenant_id      Azure AD tenant ID
  sharepoint_client_id      Azure app client ID (with Sites.ReadWrite.All)
  sharepoint_client_secret  Azure app client secret
  sharepoint_site_url       SharePoint site URL (e.g. https://contoso.sharepoint.com/sites/deals)
  sharepoint_folder         Target folder path in the document library (default: root)

Microsoft Graph API docs: https://learn.microsoft.com/en-us/graph/api/driveitem-put-content
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_GRAPH_BASE = "https://graph.microsoft.com/v1.0"
_TOKEN_URL = "https://login.microsoftonline.com/{tenant_id}/oauth2/v2.0/token"
_TIMEOUT = httpx.Timeout(connect=10.0, read=120.0, write=120.0, pool=5.0)


async def _get_access_token(tenant_id: str, client_id: str, client_secret: str) -> str:
    """Obtain an OAuth 2.0 access token via client credentials grant."""
    url = _TOKEN_URL.format(tenant_id=tenant_id)
    async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
        resp = await client.post(
            url,
            data={
                "grant_type": "client_credentials",
                "client_id": client_id,
                "client_secret": client_secret,
                "scope": "https://graph.microsoft.com/.default",
            },
        )
        resp.raise_for_status()
        token_data = resp.json()
        return token_data["access_token"]


async def _get_site_id(client: httpx.AsyncClient, site_url: str) -> str:
    """Resolve a SharePoint site URL to a Graph API site ID."""
    # site_url format: https://contoso.sharepoint.com/sites/deals
    # Graph needs: contoso.sharepoint.com:/sites/deals
    import re
    m = re.match(r"https?://([^/]+)(/.+)?", site_url)
    if not m:
        raise ValueError(f"Invalid SharePoint site URL: {site_url}")
    hostname = m.group(1)
    path = (m.group(2) or "").rstrip("/") or "/"

    resp = await client.get(f"{_GRAPH_BASE}/sites/{hostname}:{path}")
    resp.raise_for_status()
    return resp.json()["id"]


async def _get_default_drive_id(client: httpx.AsyncClient, site_id: str) -> str:
    """Get the default document library drive ID for a SharePoint site."""
    resp = await client.get(f"{_GRAPH_BASE}/sites/{site_id}/drive")
    resp.raise_for_status()
    return resp.json()["id"]


async def _upload_file(
    client: httpx.AsyncClient,
    drive_id: str,
    folder_path: str,
    filename: str,
    content: bytes,
    content_type: str = "application/octet-stream",
) -> str:
    """Upload a file to a SharePoint drive folder. Returns the web URL."""
    folder_path = folder_path.strip("/")
    if folder_path:
        upload_path = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{folder_path}/{filename}:/content"
    else:
        upload_path = f"{_GRAPH_BASE}/drives/{drive_id}/root:/{filename}:/content"

    resp = await client.put(
        upload_path,
        content=content,
        headers={"Content-Type": content_type},
    )
    resp.raise_for_status()
    item = resp.json()
    return item.get("webUrl", "")


def _build_report_json(
    deliverables: dict,
    findings: list[dict],
    target_company: str,
    pe_firm: str,
) -> bytes:
    """Serialise deliverables to a formatted JSON file."""
    report = {
        "meta": {
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "target_company": target_company,
            "pe_firm": pe_firm,
            "platform": "KEEN Due Diligence Platform",
        },
        "deliverables": deliverables,
        "findings_summary": {
            "total": len(findings),
            "critical": sum(1 for f in findings if f.get("severity") == "critical"),
            "warning": sum(1 for f in findings if f.get("severity") == "warning"),
            "info": sum(1 for f in findings if f.get("severity") == "info"),
        },
        "findings": findings,
    }
    return json.dumps(report, indent=2, default=str).encode("utf-8")


async def upload_report(
    tenant_id: str,
    client_id: str,
    client_secret: str,
    site_url: str,
    deliverables: dict,
    findings: list[dict],
    target_company: str,
    pe_firm: str,
    folder_path: str = "KEEN Reports",
    pdf_bytes: bytes | None = None,
) -> dict[str, Any]:
    """
    Upload the due diligence report to SharePoint.

    Uploads two files:
      1. {target_company}_DD_Report_{date}.json  — full structured data
      2. {target_company}_DD_Report_{date}.pdf   — PDF export (if pdf_bytes provided)

    Returns a dict with status, uploaded file URLs, and any error message.
    """
    if not all([tenant_id, client_id, client_secret, site_url]):
        return {
            "status": "skipped",
            "reason": "SharePoint credentials not fully configured "
                      "(need sharepoint_tenant_id, sharepoint_client_id, "
                      "sharepoint_client_secret, sharepoint_site_url)",
        }

    try:
        # Get access token
        token = await _get_access_token(tenant_id, client_id, client_secret)
        logger.info("SharePoint: obtained access token for tenant %s", tenant_id)

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        async with httpx.AsyncClient(base_url=_GRAPH_BASE, headers=headers, timeout=_TIMEOUT) as client:
            # Resolve site and drive
            site_id = await _get_site_id(client, site_url)
            drive_id = await _get_default_drive_id(client, site_id)
            logger.info("SharePoint: resolved site_id=%s drive_id=%s", site_id, drive_id)

            date_str = datetime.now(timezone.utc).strftime("%Y%m%d")
            safe_company = target_company.replace(" ", "_").replace("/", "-")

            uploaded_urls: list[str] = []

            # Upload JSON report
            json_filename = f"{safe_company}_DD_Report_{date_str}.json"
            json_content = _build_report_json(deliverables, findings, target_company, pe_firm)
            json_url = await _upload_file(
                client, drive_id, folder_path, json_filename, json_content, "application/json"
            )
            uploaded_urls.append(json_url)
            logger.info("SharePoint: uploaded JSON report → %s", json_url)

            # Upload PDF if provided
            if pdf_bytes:
                pdf_filename = f"{safe_company}_DD_Report_{date_str}.pdf"
                pdf_url = await _upload_file(
                    client, drive_id, folder_path, pdf_filename, pdf_bytes, "application/pdf"
                )
                uploaded_urls.append(pdf_url)
                logger.info("SharePoint: uploaded PDF report → %s", pdf_url)

        return {
            "status": "completed",
            "site_url": site_url,
            "folder": folder_path,
            "files_uploaded": len(uploaded_urls),
            "urls": uploaded_urls,
        }

    except httpx.HTTPStatusError as exc:
        body = exc.response.text[:300]
        logger.warning("SharePoint: HTTP %s error: %s", exc.response.status_code, body)
        return {
            "status": "error",
            "error": f"HTTP {exc.response.status_code}: {body}",
        }
    except Exception as exc:
        logger.exception("SharePoint: unexpected error: %s", exc)
        return {
            "status": "error",
            "error": str(exc),
        }
