"""
Email distribution channel.

Sends a formatted HTML email with executive summary + optional PDF attachment
via SMTP (supports TLS/STARTTLS).

Configuration via environment variables (or passed as kwargs):
  SMTP_HOST          SMTP server hostname          (default: smtp.gmail.com)
  SMTP_PORT          SMTP server port              (default: 587)
  SMTP_USER          SMTP username / sender email
  SMTP_PASSWORD      SMTP password or app password
  SMTP_FROM_NAME     Display name for sender       (default: KEEN Platform)
  SMTP_USE_TLS       "true" | "false"              (default: true)
"""

from __future__ import annotations

import asyncio
import logging
import os
import smtplib
import ssl
from datetime import datetime, timezone
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from functools import partial

logger = logging.getLogger(__name__)


def _recommendation_label(recommendation: str) -> str:
    return {
        "proceed": "PROCEED",
        "proceed_with_caution": "PROCEED WITH CAUTION",
        "do_not_proceed": "DO NOT PROCEED",
    }.get(recommendation, recommendation.upper().replace("_", " "))


def _recommendation_color(recommendation: str) -> str:
    return {
        "proceed": "#16A34A",
        "proceed_with_caution": "#D97706",
        "do_not_proceed": "#DC2626",
    }.get(recommendation, "#1A73E8")


def _build_html(
    target_company: str,
    pe_firm: str,
    exec_summary: dict,
    findings: list[dict],
) -> str:
    recommendation = exec_summary.get("recommendation", "proceed_with_caution")
    rec_label = _recommendation_label(recommendation)
    rec_color = _recommendation_color(recommendation)
    rationale = exec_summary.get("recommendation_rationale", "")
    key_findings = exec_summary.get("key_findings", [])
    source_count = exec_summary.get("source_count", 0)
    date_str = datetime.now(timezone.utc).strftime("%B %d, %Y")

    severity_counts: dict[str, int] = {"critical": 0, "warning": 0, "info": 0}
    for f in findings:
        sev = f.get("severity", "info").lower()
        severity_counts[sev] = severity_counts.get(sev, 0) + 1

    findings_rows = ""
    for f in findings[:15]:
        sev = f.get("severity", "info").lower()
        sev_color = {"critical": "#DC2626", "warning": "#D97706", "info": "#2563EB"}.get(
            sev, "#2563EB"
        )
        title = f.get("title", "")[:120]
        source = f.get("source_system") or "—"
        findings_rows += f"""
        <tr>
          <td style="padding:6px 10px; text-align:center;">
            <span style="background:{sev_color}; color:white; font-size:10px;
                         font-weight:bold; padding:2px 8px; border-radius:3px;">
              {sev.upper()}
            </span>
          </td>
          <td style="padding:6px 10px; color:#374151; font-size:12px;">{source}</td>
          <td style="padding:6px 10px; color:#1F2937; font-size:12px;">{title}</td>
        </tr>"""

    key_findings_html = "".join(f"<li style='margin:4px 0;'>{kf}</li>" for kf in key_findings[:6])

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>KEEN Due Diligence Report</title></head>
<body style="margin:0; padding:0; background:#F3F4F6; font-family: Helvetica, Arial, sans-serif;">
  <table width="100%" cellpadding="0" cellspacing="0" style="background:#F3F4F6; padding:32px 0;">
    <tr>
      <td align="center">
        <table width="640" cellpadding="0" cellspacing="0" style="background:white;
               border-radius:8px; overflow:hidden; box-shadow:0 2px 8px rgba(0,0,0,0.08);">

          <!-- Header -->
          <tr>
            <td style="background:#0F1B2D; padding:32px 40px; text-align:center;">
              <div style="color:#00C2A8; font-size:28px; font-weight:bold; letter-spacing:2px;">KEEN</div>
              <div style="color:#8FA8C8; font-size:11px; margin-top:4px; letter-spacing:1px;">
                DUE DILIGENCE PLATFORM
              </div>
              <div style="color:white; font-size:20px; font-weight:bold; margin-top:20px;">
                {target_company}
              </div>
              <div style="color:#B0C4DE; font-size:12px; margin-top:6px;">
                Prepared for {pe_firm} &nbsp;·&nbsp; {date_str}
              </div>
            </td>
          </tr>

          <!-- Recommendation banner -->
          <tr>
            <td style="background:{rec_color}; padding:14px 40px; text-align:center;">
              <span style="color:white; font-size:16px; font-weight:bold; letter-spacing:1px;">
                {rec_label}
              </span>
            </td>
          </tr>

          <!-- Body -->
          <tr>
            <td style="padding:32px 40px;">

              <!-- Rationale -->
              {"<p style='color:#374151; font-size:14px; line-height:1.6; margin:0 0 24px;'>" + rationale[:500] + "</p>" if rationale else ""}

              <!-- Stats row -->
              <table width="100%" cellspacing="0" cellpadding="0" style="margin-bottom:24px;">
                <tr>
                  <td style="text-align:center; background:#F9FAFB; border-radius:6px; padding:16px;">
                    <div style="font-size:24px; font-weight:bold; color:#0F1B2D;">{severity_counts['critical']}</div>
                    <div style="font-size:11px; color:#6B7280; margin-top:2px;">Critical</div>
                  </td>
                  <td width="12"></td>
                  <td style="text-align:center; background:#F9FAFB; border-radius:6px; padding:16px;">
                    <div style="font-size:24px; font-weight:bold; color:#0F1B2D;">{severity_counts['warning']}</div>
                    <div style="font-size:11px; color:#6B7280; margin-top:2px;">Warnings</div>
                  </td>
                  <td width="12"></td>
                  <td style="text-align:center; background:#F9FAFB; border-radius:6px; padding:16px;">
                    <div style="font-size:24px; font-weight:bold; color:#0F1B2D;">{source_count}</div>
                    <div style="font-size:11px; color:#6B7280; margin-top:2px;">Sources</div>
                  </td>
                </tr>
              </table>

              <!-- Key findings -->
              {"<h3 style='color:#0F1B2D; font-size:15px; margin:0 0 12px;'>Key Findings</h3><ul style='color:#374151; font-size:13px; line-height:1.7; margin:0 0 24px; padding-left:20px;'>" + key_findings_html + "</ul>" if key_findings_html else ""}

              <!-- Findings table -->
              {"<h3 style='color:#0F1B2D; font-size:15px; margin:0 0 12px;'>Findings Summary</h3>" if findings_rows else ""}
              {"<table width='100%' cellspacing='0' cellpadding='0' style='border-collapse:collapse; margin-bottom:24px;'><tr style='background:#0F1B2D;'><th style='padding:8px 10px; color:white; font-size:11px; text-align:left; width:90px;'>Severity</th><th style='padding:8px 10px; color:white; font-size:11px; text-align:left; width:100px;'>Source</th><th style='padding:8px 10px; color:white; font-size:11px; text-align:left;'>Finding</th></tr>" + findings_rows + "</table>" if findings_rows else ""}

            </td>
          </tr>

          <!-- Footer -->
          <tr>
            <td style="background:#F9FAFB; padding:20px 40px; border-top:1px solid #E5E7EB;
                       text-align:center;">
              <p style="color:#9CA3AF; font-size:10px; margin:0; line-height:1.6;">
                CONFIDENTIAL — This message and any attachments are intended solely for the
                named recipient. Generated by the KEEN Due Diligence Platform.
              </p>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>
</body>
</html>"""


def _send_email_sync(
    to_addresses: list[str],
    subject: str,
    html_body: str,
    pdf_bytes: bytes | None,
    pdf_filename: str,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    from_name: str,
    use_tls: bool,
) -> None:
    """Synchronous SMTP send (run in thread pool to avoid blocking the event loop)."""
    msg = MIMEMultipart("mixed")
    msg["From"] = f"{from_name} <{smtp_user}>"
    msg["To"] = ", ".join(to_addresses)
    msg["Subject"] = subject

    # HTML body
    html_part = MIMEText(html_body, "html", "utf-8")
    msg.attach(html_part)

    # PDF attachment (optional)
    if pdf_bytes:
        pdf_part = MIMEBase("application", "pdf")
        pdf_part.set_payload(pdf_bytes)
        encoders.encode_base64(pdf_part)
        pdf_part.add_header("Content-Disposition", f'attachment; filename="{pdf_filename}"')
        msg.attach(pdf_part)

    context = ssl.create_default_context()

    if use_tls and smtp_port == 465:
        # Implicit TLS
        with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_addresses, msg.as_string())
    else:
        # STARTTLS (port 587) or plain (port 25)
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            if use_tls:
                server.starttls(context=context)
                server.ehlo()
            if smtp_user and smtp_password:
                server.login(smtp_user, smtp_password)
            server.sendmail(smtp_user, to_addresses, msg.as_string())


async def send_report(
    to_addresses: list[str],
    deliverables: dict,
    findings: list[dict],
    target_company: str,
    pe_firm: str,
    pdf_bytes: bytes | None = None,
    smtp_host: str = "",
    smtp_port: int = 0,
    smtp_user: str = "",
    smtp_password: str = "",
    from_name: str = "",
    use_tls: bool = True,
) -> dict:
    """
    Send the due diligence report via email.

    SMTP settings are loaded from environment variables if not provided.

    Args:
        to_addresses:   List of recipient email addresses.
        deliverables:   Full deliverables dict from delivery agent.
        findings:       List of finding dicts for the table.
        target_company: Name of the company being diligenced.
        pe_firm:        Name of the PE firm.
        pdf_bytes:      Optional PDF bytes to attach.
        smtp_*:         SMTP configuration (falls back to env vars).

    Returns:
        dict with status and any error details.
    """
    # Apply env-variable fallbacks
    smtp_host = smtp_host or os.environ.get("SMTP_HOST", "smtp.gmail.com")
    smtp_port = smtp_port or int(os.environ.get("SMTP_PORT", "587"))
    smtp_user = smtp_user or os.environ.get("SMTP_USER", "")
    smtp_password = smtp_password or os.environ.get("SMTP_PASSWORD", "")
    from_name = from_name or os.environ.get("SMTP_FROM_NAME", "KEEN Platform")
    use_tls_env = os.environ.get("SMTP_USE_TLS", "true").lower()
    if not smtp_host or not smtp_user:
        use_tls = False  # can't connect — skip TLS negotiation, will fail gracefully
    else:
        use_tls = use_tls if smtp_host else (use_tls_env == "true")

    if not smtp_user:
        return {
            "status": "error",
            "channel": "email",
            "error": "SMTP not configured (SMTP_USER missing)",
        }

    exec_summary = deliverables.get("executive_summary", {})
    recommendation = exec_summary.get("recommendation", "proceed_with_caution")
    rec_label = _recommendation_label(recommendation)
    date_str = datetime.now(timezone.utc).strftime("%b %d, %Y")

    subject = f"[KEEN] Due Diligence Report — {target_company} ({rec_label}) — {date_str}"
    html_body = _build_html(
        target_company=target_company,
        pe_firm=pe_firm,
        exec_summary=exec_summary,
        findings=findings,
    )

    safe_name = target_company.replace(" ", "_").replace("/", "-")[:40]
    pdf_filename = f"KEEN_DiligenceReport_{safe_name}.pdf"

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            partial(
                _send_email_sync,
                to_addresses=to_addresses,
                subject=subject,
                html_body=html_body,
                pdf_bytes=pdf_bytes,
                pdf_filename=pdf_filename,
                smtp_host=smtp_host,
                smtp_port=smtp_port,
                smtp_user=smtp_user,
                smtp_password=smtp_password,
                from_name=from_name,
                use_tls=use_tls,
            ),
        )
        logger.info("Email: sent report to %s for %s", to_addresses, target_company)
        return {"status": "sent", "channel": "email", "recipients": to_addresses}
    except Exception as exc:
        logger.exception("Email distribution failed: %s", exc)
        return {"status": "error", "channel": "email", "error": str(exc)}
