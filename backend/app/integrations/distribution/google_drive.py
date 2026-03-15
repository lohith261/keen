"""
Google Drive distribution connector.

Uploads KEEN due diligence reports (PDF + Excel) to a Google Drive folder
using a Google Service Account with Drive scope.

The service account JSON is reused from the ``google_sheets`` vault credential
so users only need to configure one set of Google credentials.

Configuration (from google_sheets vault credentials):
  service_account_json   Google service account key JSON (required)
  folder_id              Google Drive folder ID to upload into (optional)
  share_email            Email address to grant writer access (optional)

Google Drive API docs: https://developers.google.com/drive/api/v3/reference/files/create
"""

from __future__ import annotations

import json
import logging
from typing import Any

import httpx
from google.auth.transport.requests import Request  # type: ignore[import]
from google.oauth2 import service_account  # type: ignore[import]

logger = logging.getLogger(__name__)

_DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.file",
    "https://www.googleapis.com/auth/drive",
]
_UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files?uploadType=multipart"
_PERMISSIONS_URL = "https://www.googleapis.com/drive/v3/files/{file_id}/permissions"
_TIMEOUT = httpx.Timeout(connect=15.0, read=180.0, write=180.0, pool=5.0)

# ── Internal helpers ──────────────────────────────────────────────────────────


def _get_token(service_account_info: dict) -> str:
    """Return a short-lived Bearer token for the service account."""
    creds = service_account.Credentials.from_service_account_info(
        service_account_info,
        scopes=_DRIVE_SCOPES,
    )
    creds.refresh(Request())
    return creds.token  # type: ignore[return-value]


def _upload_file(
    *,
    token: str,
    filename: str,
    mime_type: str,
    content: bytes,
    folder_id: str | None,
) -> str:
    """Upload *content* to Drive and return the new file's ID."""
    boundary = "keen_drive_multipart_20250601"

    metadata: dict[str, Any] = {"name": filename, "mimeType": mime_type}
    if folder_id:
        metadata["parents"] = [folder_id]

    # Multipart body: JSON metadata part + binary content part
    meta_bytes = json.dumps(metadata).encode()
    body = (
        f"--{boundary}\r\n"
        f"Content-Type: application/json; charset=UTF-8\r\n\r\n"
    ).encode()
    body += meta_bytes
    body += f"\r\n--{boundary}\r\n".encode()
    body += f"Content-Type: {mime_type}\r\n\r\n".encode()
    body += content
    body += f"\r\n--{boundary}--".encode()

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": f"multipart/related; boundary={boundary}",
    }

    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(_UPLOAD_URL, headers=headers, content=body)
        resp.raise_for_status()
        return resp.json()["id"]


def _set_anyone_reader(token: str, file_id: str) -> None:
    """Grant 'anyone with link → reader' permission."""
    url = _PERMISSIONS_URL.format(file_id=file_id)
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "anyone", "role": "reader"},
        )
        resp.raise_for_status()


def _share_with_email(token: str, file_id: str, email: str) -> None:
    """Grant a specific email address writer access."""
    url = _PERMISSIONS_URL.format(file_id=file_id)
    with httpx.Client(timeout=_TIMEOUT) as client:
        resp = client.post(
            url,
            headers={"Authorization": f"Bearer {token}"},
            json={"type": "user", "role": "writer", "emailAddress": email},
        )
        # Non-fatal — log and continue
        if resp.is_error:
            logger.warning(
                "Could not share Drive file %s with %s: %s", file_id, email, resp.text
            )


# ── Public API ────────────────────────────────────────────────────────────────


def upload_report(
    *,
    service_account_info: dict,
    target_company: str,
    deliverables: dict,
    findings: list[dict],
    pdf_bytes: bytes | None = None,
    excel_bytes: bytes | None = None,
    folder_id: str | None = None,
    share_email: str | None = None,
) -> dict:
    """
    Upload PDF and/or Excel report to Google Drive.

    At least one of *pdf_bytes* or *excel_bytes* must be provided.

    Returns a dict::

        {
            "status": "completed",
            "pdf": {"file_id": "...", "url": "https://drive.google.com/file/d/.../view"},
            "excel": {"file_id": "...", "url": "..."},
            "folder_id": "...",   # None if uploaded to root
        }
    """
    if pdf_bytes is None and excel_bytes is None:
        return {"status": "skipped", "reason": "no report bytes provided"}

    safe_name = "".join(c if c.isalnum() or c in " _-" else "_" for c in target_company)

    try:
        token = _get_token(service_account_info)
    except Exception as exc:
        logger.exception("Failed to obtain Google Drive token: %s", exc)
        return {"status": "error", "error": f"auth failed: {exc}"}

    result: dict[str, Any] = {"status": "completed", "folder_id": folder_id}

    # Upload PDF
    if pdf_bytes:
        try:
            pdf_id = _upload_file(
                token=token,
                filename=f"KEEN_DiligenceReport_{safe_name}.pdf",
                mime_type="application/pdf",
                content=pdf_bytes,
                folder_id=folder_id,
            )
            _set_anyone_reader(token, pdf_id)
            if share_email:
                _share_with_email(token, pdf_id, share_email)
            result["pdf"] = {
                "file_id": pdf_id,
                "url": f"https://drive.google.com/file/d/{pdf_id}/view",
            }
            logger.info("Uploaded PDF to Drive: %s (file_id=%s)", safe_name, pdf_id)
        except Exception as exc:
            logger.exception("PDF upload to Drive failed: %s", exc)
            result["pdf"] = {"error": str(exc)}
            result["status"] = "partial"

    # Upload Excel
    if excel_bytes:
        try:
            xlsx_id = _upload_file(
                token=token,
                filename=f"KEEN_DiligenceReport_{safe_name}.xlsx",
                mime_type=(
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ),
                content=excel_bytes,
                folder_id=folder_id,
            )
            _set_anyone_reader(token, xlsx_id)
            if share_email:
                _share_with_email(token, xlsx_id, share_email)
            result["excel"] = {
                "file_id": xlsx_id,
                "url": f"https://drive.google.com/file/d/{xlsx_id}/view",
            }
            logger.info(
                "Uploaded Excel to Drive: %s (file_id=%s)", safe_name, xlsx_id
            )
        except Exception as exc:
            logger.exception("Excel upload to Drive failed: %s", exc)
            result["excel"] = {"error": str(exc)}
            if result["status"] == "completed":
                result["status"] = "partial"

    return result
