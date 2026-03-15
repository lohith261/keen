"""
Google Sheets financial model export for KEEN due diligence reports.

Creates a structured Google Spreadsheet from pipeline deliverables with:
  - Cover sheet (engagement metadata)
  - Executive Summary tab
  - Key Findings tab (colour-coded by severity via conditional formatting)
  - One data tab per source (Salesforce, NetSuite, Bloomberg, etc.)
  - Compliance tab

Uses gspread + google-auth for pure-Python Google Sheets API access.
Authenticates via a Google Service Account JSON key supplied by the user.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

GSPREAD_AVAILABLE = False
try:
    import gspread
    from google.oauth2.service_account import Credentials as SACredentials

    GSPREAD_AVAILABLE = True
except ImportError:
    logger.warning("gspread / google-auth not installed; Google Sheets export disabled")

# ── Colour palette (RGB hex without #) ─────────────────────────────────────
_NAVY   = {"red": 0.039, "green": 0.086, "blue": 0.157}   # #0A1628
_BLUE   = {"red": 0.118, "green": 0.227, "blue": 0.373}   # #1E3A5F
_ACCENT = {"red": 0.145, "green": 0.388, "blue": 0.922}   # #2563EB
_WHITE  = {"red": 1.0,   "green": 1.0,   "blue": 1.0}
_LIGHT  = {"red": 0.941, "green": 0.957, "blue": 0.973}   # #F0F4F8
_GREEN  = {"red": 0.086, "green": 0.639, "blue": 0.290}   # #16A34A
_AMBER  = {"red": 0.851, "green": 0.467, "blue": 0.024}   # #D97706
_RED    = {"red": 0.863, "green": 0.149, "blue": 0.149}   # #DC2626
_GREY   = {"red": 0.420, "green": 0.447, "blue": 0.502}   # #6B7280

_SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]

# ── Helpers ──────────────────────────────────────────────────────────────────

def _color(d: dict) -> dict:
    return {"red": d["red"], "green": d["green"], "blue": d["blue"]}


def _bg(color: dict) -> dict:
    return {"backgroundColor": _color(color)}


def _fmt(bold=False, font_size=10, fg=None, bg=None, h_align="LEFT") -> dict:
    tf = {"bold": bold, "fontSize": font_size}
    if fg:
        tf["foregroundColor"] = _color(fg)
    out: dict = {"textFormat": tf, "horizontalAlignment": h_align}
    if bg:
        out["backgroundColor"] = _color(bg)
    return out


def _header_fmt(size=11, bg_color=None) -> dict:
    return _fmt(bold=True, font_size=size, fg=_WHITE, bg=bg_color or _NAVY, h_align="CENTER")


def _cell_req(sheet_id: int, row: int, col: int, value: Any, fmt: dict | None = None) -> dict:
    """Build a single updateCells request dict."""
    user_entered = {}
    if isinstance(value, (int, float)):
        user_entered["numberValue"] = value
    elif isinstance(value, bool):
        user_entered["boolValue"] = value
    else:
        user_entered["stringValue"] = str(value) if value is not None else ""

    cell: dict = {"userEnteredValue": user_entered}
    if fmt:
        cell["userEnteredFormat"] = fmt

    return {
        "updateCells": {
            "rows": [{"values": [cell]}],
            "fields": "userEnteredValue,userEnteredFormat",
            "start": {"sheetId": sheet_id, "rowIndex": row, "columnIndex": col},
        }
    }


def _merge_req(sheet_id: int, r0: int, r1: int, c0: int, c1: int) -> dict:
    return {
        "mergeCells": {
            "range": {"sheetId": sheet_id, "startRowIndex": r0, "endRowIndex": r1,
                      "startColumnIndex": c0, "endColumnIndex": c1},
            "mergeType": "MERGE_ALL",
        }
    }


def _col_width_req(sheet_id: int, col: int, pixels: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "COLUMNS",
                      "startIndex": col, "endIndex": col + 1},
            "properties": {"pixelSize": pixels},
            "fields": "pixelSize",
        }
    }


def _row_height_req(sheet_id: int, row: int, pixels: int) -> dict:
    return {
        "updateDimensionProperties": {
            "range": {"sheetId": sheet_id, "dimension": "ROWS",
                      "startIndex": row, "endIndex": row + 1},
            "properties": {"pixelSize": pixels},
            "fields": "pixelSize",
        }
    }


def _freeze_req(sheet_id: int, rows: int = 1, cols: int = 0) -> dict:
    return {
        "updateSheetProperties": {
            "properties": {
                "sheetId": sheet_id,
                "gridProperties": {"frozenRowCount": rows, "frozenColumnCount": cols},
            },
            "fields": "gridProperties.frozenRowCount,gridProperties.frozenColumnCount",
        }
    }


# ── Sheet builders ──────────────────────────────────────────────────────────

def _build_cover_requests(sheet_id: int, target_company: str, pe_firm: str, deliverables: dict) -> list[dict]:
    reqs: list[dict] = []
    exec_summary = deliverables.get("executive_summary", {})

    # Title
    reqs.append(_cell_req(sheet_id, 1, 1, "KEEN DUE DILIGENCE PLATFORM",
                           _fmt(bold=True, font_size=10, fg=_GREY)))
    reqs.append(_merge_req(sheet_id, 1, 2, 1, 4))

    reqs.append(_cell_req(sheet_id, 2, 1, f"Financial Due Diligence — {target_company}",
                           _fmt(bold=True, font_size=22, fg=_NAVY)))
    reqs.append(_merge_req(sheet_id, 2, 4, 1, 4))
    reqs.append(_row_height_req(sheet_id, 2, 60))

    reqs.append(_cell_req(sheet_id, 5, 1, f"Prepared for {pe_firm}",
                           _fmt(font_size=13, fg=_BLUE)))
    reqs.append(_merge_req(sheet_id, 5, 6, 1, 4))

    reqs.append(_cell_req(sheet_id, 6, 1,
                           datetime.now(timezone.utc).strftime("%B %d, %Y"),
                           _fmt(font_size=11, fg=_GREY)))

    # Divider row bg
    for col in range(1, 4):
        reqs.append(_cell_req(sheet_id, 8, col, "", _fmt(bg=_ACCENT)))
    reqs.append(_row_height_req(sheet_id, 8, 6))

    # Metadata
    meta_rows = [
        ("Engagement Type",  "Financial Due Diligence"),
        ("Target Company",   target_company),
        ("Client",           pe_firm),
        ("Report Date",      datetime.now(timezone.utc).strftime("%Y-%m-%d")),
        ("Recommendation",   exec_summary.get("recommendation", "—")),
        ("Confidence Level", exec_summary.get("confidence_level", "—")),
    ]
    reqs.append(_cell_req(sheet_id, 10, 1, "ENGAGEMENT DETAILS",
                           _fmt(bold=True, font_size=9, fg=_GREY)))
    for i, (label, value) in enumerate(meta_rows, start=11):
        reqs.append(_cell_req(sheet_id, i, 1, label, _fmt(bold=True)))
        reqs.append(_cell_req(sheet_id, i, 2, value, _fmt()))

    # Confidential notice
    reqs.append(_cell_req(sheet_id, 19, 1,
                           "CONFIDENTIAL — FOR INTERNAL USE ONLY. Not for distribution without prior written consent.",
                           _fmt(font_size=9, fg=_GREY)))
    reqs.append(_merge_req(sheet_id, 19, 20, 1, 4))

    # Column widths
    reqs += [
        _col_width_req(sheet_id, 0, 30),
        _col_width_req(sheet_id, 1, 240),
        _col_width_req(sheet_id, 2, 240),
        _col_width_req(sheet_id, 3, 120),
    ]
    return reqs


def _build_exec_summary_requests(sheet_id: int, exec_summary: dict) -> list[dict]:
    reqs: list[dict] = []

    reqs.append(_cell_req(sheet_id, 0, 0, "EXECUTIVE SUMMARY",
                           _fmt(bold=True, font_size=16, fg=_NAVY)))
    reqs.append(_merge_req(sheet_id, 0, 1, 0, 3))
    reqs.append(_row_height_req(sheet_id, 0, 36))

    rec = exec_summary.get("recommendation", "PROCEED")
    rec_color = {"PROCEED": _GREEN, "PROCEED WITH CONDITIONS": _AMBER, "DO NOT PROCEED": _RED}.get(rec, _ACCENT)
    reqs.append(_cell_req(sheet_id, 2, 0, f"Recommendation: {rec}",
                           _fmt(bold=True, font_size=12, fg=_WHITE, bg=rec_color, h_align="CENTER")))
    reqs.append(_merge_req(sheet_id, 2, 3, 0, 3))
    reqs.append(_row_height_req(sheet_id, 2, 30))

    # KPI section header
    row = 4
    reqs.append(_cell_req(sheet_id, row, 0, "KEY METRICS",
                           _fmt(bold=True, font_size=9, fg=_GREY, bg=_LIGHT)))
    reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
    row += 1

    kpis = [
        ("Critical Findings",  exec_summary.get("critical_findings_count", 0)),
        ("Warning Findings",   exec_summary.get("warning_findings_count", 0)),
        ("Data Sources",       exec_summary.get("sources_analyzed", 0)),
        ("Confidence Level",   exec_summary.get("confidence_level", "—")),
    ]
    for label, value in kpis:
        reqs.append(_cell_req(sheet_id, row, 0, label, _fmt(bold=True)))
        reqs.append(_cell_req(sheet_id, row, 1, value, _fmt()))
        row += 1

    # Key findings
    row += 1
    reqs.append(_cell_req(sheet_id, row, 0, "KEY FINDINGS",
                           _fmt(bold=True, font_size=9, fg=_GREY, bg=_LIGHT)))
    reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
    row += 1
    for finding in exec_summary.get("key_findings", []):
        reqs.append(_cell_req(sheet_id, row, 0, f"• {finding}", _fmt()))
        reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
        reqs.append(_row_height_req(sheet_id, row, 24))
        row += 1

    # Narrative
    row += 1
    reqs.append(_cell_req(sheet_id, row, 0, "SUMMARY NARRATIVE",
                           _fmt(bold=True, font_size=9, fg=_GREY, bg=_LIGHT)))
    reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
    row += 1
    reqs.append(_cell_req(sheet_id, row, 0, exec_summary.get("narrative", ""), _fmt()))
    reqs.append(_merge_req(sheet_id, row, row + 5, 0, 3))
    reqs.append(_row_height_req(sheet_id, row, 90))

    reqs += [_col_width_req(sheet_id, i, w) for i, w in enumerate([200, 120, 300, 120])]
    return reqs


def _build_findings_requests(sheet_id: int, findings: list[dict]) -> list[dict]:
    reqs: list[dict] = []

    reqs.append(_cell_req(sheet_id, 0, 0, "KEY FINDINGS",
                           _fmt(bold=True, font_size=16, fg=_NAVY)))
    reqs.append(_merge_req(sheet_id, 0, 1, 0, 5))

    headers = ["Source System", "Type", "Severity", "Finding", "Review Required"]
    for col, h in enumerate(headers):
        reqs.append(_cell_req(sheet_id, 2, col, h, _header_fmt(size=10)))
    reqs.append(_row_height_req(sheet_id, 2, 22))
    reqs.append(_freeze_req(sheet_id, rows=3))

    sev_color = {"critical": _RED, "warning": _AMBER, "info": _ACCENT}

    for row_idx, finding in enumerate(findings, start=3):
        sev = finding.get("severity", "info")
        color = sev_color.get(sev, _ACCENT)

        vals = [
            finding.get("source_system", ""),
            finding.get("finding_type", finding.get("type", "")),
            sev.upper(),
            finding.get("title", ""),
            "✓" if finding.get("requires_human_review") else "",
        ]
        for col, val in enumerate(vals):
            fmt = _fmt(bold=(col == 2), fg=_WHITE if col == 2 else None,
                       bg=color if col == 2 else None)
            reqs.append(_cell_req(sheet_id, row_idx, col, val, fmt))
        reqs.append(_row_height_req(sheet_id, row_idx, 20))

    reqs += [_col_width_req(sheet_id, i, w) for i, w in
             enumerate([150, 120, 90, 360, 80])]
    return reqs


def _build_data_tab_requests(sheet_id: int, source_name: str, data: dict) -> list[dict]:
    reqs: list[dict] = []
    display = source_name.replace("_", " ").title()

    reqs.append(_cell_req(sheet_id, 0, 0, display,
                           _fmt(bold=True, font_size=14, fg=_NAVY)))
    reqs.append(_merge_req(sheet_id, 0, 1, 0, 5))

    row = 2
    for extraction_type, records in data.items():
        if not records:
            continue

        label = extraction_type.replace("_", " ").upper()
        reqs.append(_cell_req(sheet_id, row, 0, label,
                               _fmt(bold=True, font_size=9, fg=_GREY, bg=_LIGHT)))
        reqs.append(_merge_req(sheet_id, row, row + 1, 0, 8))
        row += 1

        if not isinstance(records, list) or not records:
            reqs.append(_cell_req(sheet_id, row, 0, "No data extracted", _fmt(fg=_GREY)))
            row += 2
            continue

        first = records[0] if isinstance(records[0], dict) else {}
        keys = list(first.keys())[:8]

        for col, key in enumerate(keys):
            reqs.append(_cell_req(sheet_id, row, col,
                                   key.replace("_", " ").title(),
                                   _header_fmt(size=9, bg_color=_BLUE)))
        reqs.append(_row_height_req(sheet_id, row, 20))
        row += 1

        for record in records[:200]:
            if isinstance(record, dict):
                for col, key in enumerate(keys):
                    reqs.append(_cell_req(sheet_id, row, col, record.get(key, ""), _fmt()))
            row += 1

        row += 1  # gap

    return reqs


def _build_compliance_requests(sheet_id: int, compliance: dict) -> list[dict]:
    reqs: list[dict] = []

    reqs.append(_cell_req(sheet_id, 0, 0, "COMPLIANCE REVIEW",
                           _fmt(bold=True, font_size=16, fg=_NAVY)))
    reqs.append(_merge_req(sheet_id, 0, 1, 0, 3))

    status = compliance.get("status", "unknown")
    status_color = {"passed": _GREEN, "warnings": _AMBER, "failed": _RED}.get(status, _GREY)
    reqs.append(_cell_req(sheet_id, 2, 0, f"Status: {status.upper()}",
                           _fmt(bold=True, font_size=12, fg=_WHITE, bg=status_color, h_align="CENTER")))
    reqs.append(_merge_req(sheet_id, 2, 3, 0, 3))
    reqs.append(_row_height_req(sheet_id, 2, 30))

    row = 4
    summary = [
        ("Checks Passed", compliance.get("checks_passed", 0)),
        ("Checks Warned", compliance.get("checks_warned", 0)),
        ("Checks Failed", compliance.get("checks_failed", 0)),
        ("PII Hits",      len(compliance.get("pii_hits", []))),
    ]
    for label, value in summary:
        reqs.append(_cell_req(sheet_id, row, 0, label, _fmt(bold=True)))
        reqs.append(_cell_req(sheet_id, row, 1, value, _fmt()))
        row += 1

    row += 1
    issues = compliance.get("issues", []) + compliance.get("warnings", [])
    if issues:
        reqs.append(_cell_req(sheet_id, row, 0, "ISSUES & WARNINGS",
                               _fmt(bold=True, font_size=9, fg=_GREY, bg=_LIGHT)))
        reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
        row += 1
        for issue in issues:
            reqs.append(_cell_req(sheet_id, row, 0, f"• {issue}", _fmt()))
            reqs.append(_merge_req(sheet_id, row, row + 1, 0, 3))
            reqs.append(_row_height_req(sheet_id, row, 28))
            row += 1

    reqs += [_col_width_req(sheet_id, i, w) for i, w in enumerate([200, 90, 340, 120])]
    return reqs


# ── Public API ──────────────────────────────────────────────────────────────

def create_google_sheet(
    deliverables: dict,
    findings: list[dict],
    source_data: dict,
    target_company: str,
    pe_firm: str,
    service_account_info: dict,
    share_email: str | None = None,
) -> str:
    """
    Create a Google Sheet from KEEN pipeline output.

    Args:
        deliverables:         Dict from delivery agent state.
        findings:             List of finding dicts.
        source_data:          Raw extracted data keyed by source name.
        target_company:       Name of the company being diligenced.
        pe_firm:              Name of the PE firm (client).
        service_account_info: Parsed Google service-account key dict.
        share_email:          Optional email address to share the sheet with.

    Returns:
        URL of the created Google Spreadsheet.
    """
    if not GSPREAD_AVAILABLE:
        raise RuntimeError(
            "gspread and google-auth are required for Google Sheets export. "
            "Install them with: pip install gspread google-auth"
        )

    # Authenticate
    creds = SACredentials.from_service_account_info(service_account_info, scopes=_SCOPES)
    gc = gspread.authorize(creds)  # type: ignore[attr-defined]

    title = f"KEEN — {target_company} — {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"
    ss = gc.create(title)
    spreadsheet_id = ss.id

    # ── Use batchUpdate for efficient formatting ────────────────────────────
    sheet_requests: list[dict] = []

    # 1. Rename the default sheet to "Cover" and collect its ID
    first_sheet = ss.sheet1
    cover_id = first_sheet.id
    sheet_requests.append({
        "updateSheetProperties": {
            "properties": {"sheetId": cover_id, "title": "Cover"},
            "fields": "title",
        }
    })

    # Helper: add a new sheet and return its properties dict
    def _add_sheet(title: str) -> dict:
        resp = ss.add_worksheet(title=title, rows=500, cols=20)
        return {"sheetId": resp.id, "title": title, "ref": resp}

    # 2. Build all tabs
    tabs = [
        ("Executive Summary", lambda sid: _build_exec_summary_requests(sid, deliverables.get("executive_summary", {}))),
        ("Key Findings",      lambda sid: _build_findings_requests(sid, findings)),
    ]

    # Source data tabs
    for source_name, data in source_data.items():
        if data:
            label = source_name.replace("_", " ").title()[:31]
            tabs.append((label, lambda sid, sn=source_name, d=data: _build_data_tab_requests(sid, sn, d)))

    # Compliance tab
    compliance = deliverables.get("compliance", {})
    if compliance:
        tabs.append(("Compliance", lambda sid: _build_compliance_requests(sid, compliance)))

    # Create sheets and accumulate formatting requests
    all_requests: list[dict] = sheet_requests + _build_cover_requests(cover_id, target_company, pe_firm, deliverables)

    for tab_title, req_builder in tabs:
        ws_resp = ss.add_worksheet(title=tab_title, rows=500, cols=20)
        all_requests.extend(req_builder(ws_resp.id))

    # Execute all formatting in one batch
    if all_requests:
        ss.batch_update({"requests": all_requests})

    # Share with caller
    if share_email:
        ss.share(share_email, perm_type="user", role="writer", notify=False)

    url = f"https://docs.google.com/spreadsheets/d/{spreadsheet_id}"
    logger.info("Google Sheets: created '%s' at %s", title, url)
    return url
