"""
PDF report generator for KEEN due diligence deliverables.

Generates a professional multi-page PDF from the delivery agent output,
including cover page, executive summary, detailed analysis sections,
findings table, and data sources.

Uses ReportLab for pure-Python PDF generation (no system dependencies).
"""

from __future__ import annotations

import io
import textwrap
from datetime import datetime, timezone
from typing import Any

# ── ReportLab imports ─────────────────────────────────────────────────────────
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
    from reportlab.lib.pagesizes import A4, letter
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import cm, inch
    from reportlab.platypus import (
        HRFlowable,
        PageBreak,
        Paragraph,
        SimpleDocTemplate,
        Spacer,
        Table,
        TableStyle,
    )
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


# ── Brand colours ─────────────────────────────────────────────────────────────
KEEN_NAVY = colors.HexColor("#0F1B2D")
KEEN_BLUE = colors.HexColor("#1A73E8")
KEEN_LIGHT = colors.HexColor("#F8FAFF")
KEEN_ACCENT = colors.HexColor("#00C2A8")

SEV_CRITICAL = colors.HexColor("#DC2626")   # red
SEV_WARNING = colors.HexColor("#D97706")    # amber
SEV_INFO = colors.HexColor("#2563EB")       # blue

REC_PROCEED = colors.HexColor("#16A34A")           # green
REC_CAUTION = colors.HexColor("#D97706")           # amber
REC_DO_NOT_PROCEED = colors.HexColor("#DC2626")    # red

PAGE_SIZE = letter  # 8.5 × 11 in


def _recommendation_color(recommendation: str) -> Any:
    mapping = {
        "proceed": REC_PROCEED,
        "proceed_with_caution": REC_CAUTION,
        "do_not_proceed": REC_DO_NOT_PROCEED,
    }
    return mapping.get(recommendation, KEEN_BLUE)


def _recommendation_label(recommendation: str) -> str:
    mapping = {
        "proceed": "PROCEED",
        "proceed_with_caution": "PROCEED WITH CAUTION",
        "do_not_proceed": "DO NOT PROCEED",
    }
    return mapping.get(recommendation, recommendation.upper().replace("_", " "))


def _severity_color(severity: str) -> Any:
    return {"critical": SEV_CRITICAL, "warning": SEV_WARNING, "info": SEV_INFO}.get(
        severity.lower(), SEV_INFO
    )


def _truncate(text: str, max_chars: int = 500) -> str:
    if len(text) <= max_chars:
        return text
    return text[:max_chars].rsplit(" ", 1)[0] + " …"


# ── Style factory ─────────────────────────────────────────────────────────────

def _build_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()

    return {
        "cover_title": ParagraphStyle(
            "cover_title",
            fontSize=28,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=8,
            fontName="Helvetica-Bold",
            leading=34,
        ),
        "cover_subtitle": ParagraphStyle(
            "cover_subtitle",
            fontSize=14,
            textColor=colors.HexColor("#B0C4DE"),
            alignment=TA_CENTER,
            spaceAfter=4,
            fontName="Helvetica",
        ),
        "cover_meta": ParagraphStyle(
            "cover_meta",
            fontSize=10,
            textColor=colors.HexColor("#8FA8C8"),
            alignment=TA_CENTER,
            fontName="Helvetica",
        ),
        "rec_label": ParagraphStyle(
            "rec_label",
            fontSize=16,
            textColor=colors.white,
            alignment=TA_CENTER,
            fontName="Helvetica-Bold",
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontSize=16,
            textColor=KEEN_NAVY,
            fontName="Helvetica-Bold",
            spaceBefore=18,
            spaceAfter=8,
            leading=20,
        ),
        "sub_header": ParagraphStyle(
            "sub_header",
            fontSize=12,
            textColor=KEEN_NAVY,
            fontName="Helvetica-Bold",
            spaceBefore=12,
            spaceAfter=4,
            leading=16,
        ),
        "body": ParagraphStyle(
            "body",
            fontSize=10,
            textColor=colors.HexColor("#1F2937"),
            fontName="Helvetica",
            spaceAfter=6,
            leading=15,
        ),
        "bullet": ParagraphStyle(
            "bullet",
            fontSize=10,
            textColor=colors.HexColor("#374151"),
            fontName="Helvetica",
            leftIndent=16,
            spaceAfter=4,
            leading=14,
            bulletIndent=4,
        ),
        "caption": ParagraphStyle(
            "caption",
            fontSize=8,
            textColor=colors.HexColor("#6B7280"),
            fontName="Helvetica",
            spaceAfter=2,
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=8,
            textColor=colors.HexColor("#9CA3AF"),
            fontName="Helvetica",
            alignment=TA_CENTER,
        ),
        "table_header": ParagraphStyle(
            "table_header",
            fontSize=9,
            textColor=colors.white,
            fontName="Helvetica-Bold",
            alignment=TA_CENTER,
        ),
        "table_cell": ParagraphStyle(
            "table_cell",
            fontSize=9,
            textColor=colors.HexColor("#1F2937"),
            fontName="Helvetica",
            leading=12,
        ),
        "highlight": ParagraphStyle(
            "highlight",
            fontSize=11,
            textColor=KEEN_NAVY,
            fontName="Helvetica-Bold",
            spaceAfter=6,
            leading=16,
        ),
    }


# ── Page template (header + footer) ──────────────────────────────────────────

class _KENNCanvas:
    """Mixin that draws the running header and footer on every page (except cover)."""

    def __init__(self, *args, company_name: str = "", target_company: str = "", **kwargs):
        self._company_name = company_name
        self._target_company = target_company
        super().__init__(*args, **kwargs)  # type: ignore[call-arg]

    def afterPage(self):  # noqa: N802 – reportlab naming convention
        self.setFont("Helvetica", 8)
        page_num = self._pageNumber  # type: ignore[attr-defined]
        w, h = PAGE_SIZE

        if page_num > 1:
            # Header bar
            self.setFillColor(KEEN_NAVY)
            self.rect(0, h - 0.45 * inch, w, 0.45 * inch, fill=1, stroke=0)
            self.setFillColor(colors.white)
            self.setFont("Helvetica-Bold", 8)
            self.drawString(0.4 * inch, h - 0.28 * inch, "KEEN Due Diligence Platform")
            self.setFont("Helvetica", 8)
            self.drawRightString(w - 0.4 * inch, h - 0.28 * inch, self._target_company)

            # Footer
            self.setFillColor(colors.HexColor("#6B7280"))
            self.drawCentredString(w / 2, 0.3 * inch, f"Page {page_num}")
            self.drawString(0.4 * inch, 0.3 * inch, "CONFIDENTIAL — For authorized recipients only")
            self.setFont("Helvetica-Bold", 8)
            self.drawRightString(w - 0.4 * inch, 0.3 * inch, "KEEN")


# ── Cover page builder ────────────────────────────────────────────────────────

def _build_cover(
    styles: dict,
    target_company: str,
    pe_firm: str,
    recommendation: str,
    date_str: str,
    source_count: int,
) -> list:
    """Return cover-page flowables (full dark-background cover)."""
    story = []

    # Dark navy block — simulated with a colored table cell spanning the page
    rec_color = _recommendation_color(recommendation)
    rec_label = _recommendation_label(recommendation)

    # Title block table (full width, dark bg)
    title_data = [
        [Paragraph("KEEN", ParagraphStyle("brand", fontSize=36, textColor=KEEN_ACCENT,
                                           fontName="Helvetica-Bold", alignment=TA_CENTER))],
        [Paragraph("DUE DILIGENCE REPORT", ParagraphStyle("dd", fontSize=13, textColor=colors.HexColor("#8FA8C8"),
                                                             fontName="Helvetica", alignment=TA_CENTER))],
        [Spacer(1, 0.3 * inch)],
        [Paragraph(target_company, ParagraphStyle("co", fontSize=26, textColor=colors.white,
                                                    fontName="Helvetica-Bold", alignment=TA_CENTER, leading=32))],
        [Spacer(1, 0.15 * inch)],
        [Paragraph(f"Prepared for {pe_firm}", ParagraphStyle("pf", fontSize=11,
                                                               textColor=colors.HexColor("#B0C4DE"),
                                                               fontName="Helvetica", alignment=TA_CENTER))],
        [Paragraph(date_str, ParagraphStyle("dt", fontSize=10, textColor=colors.HexColor("#8FA8C8"),
                                             fontName="Helvetica", alignment=TA_CENTER))],
        [Spacer(1, 0.5 * inch)],
        # Recommendation badge
        [Table(
            [[Paragraph(rec_label, ParagraphStyle("rl", fontSize=14, textColor=colors.white,
                                                   fontName="Helvetica-Bold", alignment=TA_CENTER))]],
            colWidths=[3.5 * inch],
            style=TableStyle([
                ("BACKGROUND", (0, 0), (-1, -1), rec_color),
                ("TOPPADDING", (0, 0), (-1, -1), 10),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 10),
                ("ROUNDEDCORNERS", [4]),
            ]),
        )],
        [Spacer(1, 0.4 * inch)],
        [Paragraph(
            f"This report was generated by the KEEN multi-agent platform across "
            f"{source_count} data source{'s' if source_count != 1 else ''}.",
            ParagraphStyle("note", fontSize=9, textColor=colors.HexColor("#6B7280"),
                           fontName="Helvetica", alignment=TA_CENTER),
        )],
        [Paragraph(
            "CONFIDENTIAL — For authorized recipients only. Not for distribution.",
            ParagraphStyle("conf", fontSize=8, textColor=colors.HexColor("#6B7280"),
                           fontName="Helvetica", alignment=TA_CENTER),
        )],
    ]

    page_w, page_h = PAGE_SIZE
    cover_table = Table(title_data, colWidths=[page_w - 1.6 * inch])
    cover_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), KEEN_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
    ]))

    story.append(Spacer(1, 1.8 * inch))
    story.append(cover_table)
    story.append(PageBreak())
    return story


# ── Executive summary builder ─────────────────────────────────────────────────

def _build_executive_summary(styles: dict, exec_summary: dict) -> list:
    story = []
    story.append(Paragraph("Executive Summary", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=2, color=KEEN_BLUE, spaceAfter=12))

    # Recommendation block
    recommendation = exec_summary.get("recommendation", "")
    rec_label = _recommendation_label(recommendation)
    rec_color = _recommendation_color(recommendation)

    rec_table = Table(
        [[Paragraph(rec_label, ParagraphStyle("rl2", fontSize=13, textColor=colors.white,
                                               fontName="Helvetica-Bold", alignment=TA_CENTER))]],
        colWidths=[4 * inch],
    )
    rec_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), rec_color),
        ("TOPPADDING", (0, 0), (-1, -1), 8),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
    ]))
    story.append(rec_table)
    story.append(Spacer(1, 0.15 * inch))

    # Rationale
    rationale = exec_summary.get("recommendation_rationale", "")
    if rationale:
        story.append(Paragraph(rationale, styles["body"]))
        story.append(Spacer(1, 0.1 * inch))

    # Key findings list
    key_findings = exec_summary.get("key_findings", [])
    if key_findings:
        story.append(Paragraph("Key Findings", styles["sub_header"]))
        for finding in key_findings:
            story.append(Paragraph(f"• {finding}", styles["bullet"]))
        story.append(Spacer(1, 0.1 * inch))

    # Risk assessment
    risk = exec_summary.get("risk_assessment", "")
    if risk:
        story.append(Paragraph("Risk Assessment", styles["sub_header"]))
        story.append(Paragraph(risk, styles["body"]))

    return story


# ── Findings table builder ─────────────────────────────────────────────────────

def _build_findings_table(styles: dict, findings: list[dict]) -> list:
    if not findings:
        return []

    story = []
    story.append(PageBreak())
    story.append(Paragraph("Findings Summary", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=2, color=KEEN_BLUE, spaceAfter=12))

    # Table headers
    col_widths = [1.1 * inch, 0.85 * inch, 1.1 * inch, 3.5 * inch]
    header_row = [
        Paragraph("Severity", styles["table_header"]),
        Paragraph("Type", styles["table_header"]),
        Paragraph("Source", styles["table_header"]),
        Paragraph("Finding", styles["table_header"]),
    ]
    rows = [header_row]

    for f in findings:
        severity = f.get("severity", "info")
        sev_color = _severity_color(severity)
        sev_label = severity.upper()

        rows.append([
            Paragraph(sev_label, ParagraphStyle(
                "sev", fontSize=9, textColor=colors.white,
                fontName="Helvetica-Bold", alignment=TA_CENTER,
            )),
            Paragraph(
                f.get("finding_type", "").replace("_", " ").title(),
                styles["table_cell"],
            ),
            Paragraph(f.get("source_system") or "—", styles["table_cell"]),
            Paragraph(_truncate(f.get("title", ""), 200), styles["table_cell"]),
        ])

    table = Table(rows, colWidths=col_widths, repeatRows=1)

    # Build per-row severity background styles
    table_styles = [
        # Header
        ("BACKGROUND", (0, 0), (-1, 0), KEEN_NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#E5E7EB")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F9FAFB")]),
    ]

    # Colour the severity cell per row
    for i, f in enumerate(findings, start=1):
        sev = f.get("severity", "info")
        table_styles.append(
            ("BACKGROUND", (0, i), (0, i), _severity_color(sev))
        )

    table.setStyle(TableStyle(table_styles))
    story.append(table)
    return story


# ── Detailed sections builder ─────────────────────────────────────────────────

def _build_detailed_sections(styles: dict, detailed_report: dict) -> list:
    sections = detailed_report.get("sections", [])
    if not sections:
        return []

    story = []
    for section in sections:
        story.append(PageBreak())
        title = section.get("section_title", "Section")
        content = section.get("content", "")
        data_points = section.get("data_points", [])
        confidence = section.get("confidence_level", "")

        story.append(Paragraph(title, styles["section_header"]))
        story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceAfter=10))

        if confidence:
            story.append(Paragraph(
                f"Confidence: {confidence.title()}",
                ParagraphStyle("conf_level", fontSize=9, textColor=colors.HexColor("#6B7280"),
                               fontName="Helvetica-Oblique", spaceAfter=8),
            ))

        # Content — split into paragraphs on newlines
        if content:
            for para_text in content.split("\n\n"):
                para_text = para_text.strip()
                if not para_text:
                    continue
                # Detect bullet lines
                if para_text.startswith("- ") or para_text.startswith("• "):
                    for line in para_text.splitlines():
                        line = line.strip().lstrip("-• ").strip()
                        if line:
                            story.append(Paragraph(f"• {line}", styles["bullet"]))
                else:
                    story.append(Paragraph(para_text, styles["body"]))

        # Data points (key metrics)
        if data_points:
            story.append(Spacer(1, 0.1 * inch))
            story.append(Paragraph("Supporting Data Points", styles["sub_header"]))
            for dp in data_points[:10]:  # cap at 10 per section
                if isinstance(dp, dict):
                    label = dp.get("label") or dp.get("name") or dp.get("metric", "")
                    value = dp.get("value") or dp.get("amount", "")
                    note = dp.get("note") or dp.get("description", "")
                    text = f"• <b>{label}</b>: {value}"
                    if note:
                        text += f" — {note}"
                    story.append(Paragraph(text, styles["bullet"]))
                else:
                    story.append(Paragraph(f"• {dp}", styles["bullet"]))

    return story


# ── Appendix / Data Sources ───────────────────────────────────────────────────

def _build_appendix(styles: dict, audit_trail: dict) -> list:
    story = []
    story.append(PageBreak())
    story.append(Paragraph("Data Sources & Methodology", styles["section_header"]))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#E5E7EB"), spaceAfter=10))

    sources = audit_trail.get("sources_accessed", [])
    if sources:
        story.append(Paragraph("Data Sources Accessed", styles["sub_header"]))
        for s in sources:
            story.append(Paragraph(f"• {s}", styles["bullet"]))
        story.append(Spacer(1, 0.1 * inch))

    story.append(Paragraph("Methodology", styles["sub_header"]))
    story.append(Paragraph(
        "This report was produced by the KEEN multi-agent due diligence platform. "
        "The Research Agent authenticated to each configured data source and extracted "
        "structured records. The Analysis Agent identified discrepancies, anomalies, and "
        "insights using statistical methods and large language model reasoning. "
        "The Delivery Agent compiled findings into this report.",
        styles["body"],
    ))

    findings_count = audit_trail.get("findings_generated", 0)
    compliance = audit_trail.get("compliance_status", "")
    story.append(Spacer(1, 0.1 * inch))
    story.append(Paragraph("Audit Summary", styles["sub_header"]))
    story.append(Paragraph(f"• Findings generated: {findings_count}", styles["bullet"]))
    if compliance:
        story.append(Paragraph(f"• Compliance status: {compliance.title()}", styles["bullet"]))
    story.append(Paragraph(
        f"• Report generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}",
        styles["bullet"],
    ))

    story.append(Spacer(1, 0.3 * inch))
    story.append(Paragraph(
        "CONFIDENTIAL NOTICE: This document contains confidential and proprietary information. "
        "It is intended solely for the named recipient and may not be reproduced, distributed, "
        "or disclosed without prior written consent. This report is not investment advice.",
        ParagraphStyle("disc", fontSize=8, textColor=colors.HexColor("#6B7280"),
                       fontName="Helvetica-Oblique", leading=12),
    ))
    return story


# ── Public API ────────────────────────────────────────────────────────────────

def generate_pdf(
    deliverables: dict,
    findings: list[dict],
    target_company: str,
    pe_firm: str,
) -> bytes:
    """
    Generate a PDF report from KEEN deliverables.

    Args:
        deliverables: Full deliverables dict from delivery agent state
                      (keys: executive_summary, detailed_report, audit_trail, …)
        findings:     List of FindingResponse dicts (from DB) for the findings table
        target_company: Name of the company being diligenced
        pe_firm:      Name of the PE firm

    Returns:
        PDF bytes ready to stream to the client.

    Raises:
        ImportError if reportlab is not installed.
    """
    if not REPORTLAB_AVAILABLE:
        raise ImportError(
            "reportlab is required for PDF export. "
            "Install it with: pip install reportlab"
        )

    buf = io.BytesIO()
    styles = _build_styles()

    doc = SimpleDocTemplate(
        buf,
        pagesize=PAGE_SIZE,
        leftMargin=0.8 * inch,
        rightMargin=0.8 * inch,
        topMargin=0.7 * inch,
        bottomMargin=0.6 * inch,
        title=f"KEEN Due Diligence — {target_company}",
        author="KEEN Platform",
        subject="Due Diligence Report",
    )

    exec_summary = deliverables.get("executive_summary", {})
    detailed_report = deliverables.get("detailed_report", {})
    audit_trail = deliverables.get("audit_trail", {})

    recommendation = exec_summary.get("recommendation", "proceed_with_caution")
    source_count = exec_summary.get("source_count", len(audit_trail.get("sources_accessed", [])))
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    story: list = []

    # 1. Cover page
    story += _build_cover(
        styles=styles,
        target_company=target_company,
        pe_firm=pe_firm,
        recommendation=recommendation,
        date_str=date_str,
        source_count=source_count,
    )

    # 2. Executive summary
    story += _build_executive_summary(styles=styles, exec_summary=exec_summary)

    # 3. Findings table
    story += _build_findings_table(styles=styles, findings=findings)

    # 4. Detailed sections
    story += _build_detailed_sections(styles=styles, detailed_report=detailed_report)

    # 5. Appendix / sources
    story += _build_appendix(styles=styles, audit_trail=audit_trail)

    doc.build(story)
    return buf.getvalue()
