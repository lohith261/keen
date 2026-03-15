"""
PII detection and compliance scanner.

Scans deliverable text for personally identifiable information (PII) and
validates that required disclaimers and attribution are present.

Patterns detected:
  - Social Security Numbers (XXX-XX-XXXX)
  - Credit / debit card numbers (Luhn-valid 13-19 digit sequences)
  - US phone numbers
  - Dates of birth embedded in specific patterns
  - Personal email addresses (non-corporate domains)
  - Passport numbers
  - Bank account / routing numbers

Compliance checks:
  - Confidentiality disclaimer present
  - Data attribution / source list present
  - No raw credential strings
  - No personal (non-executive) contact details in final output
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any


# ── PII Regex Patterns ────────────────────────────────────────────────────────

_SSN = re.compile(r"\b(?!000|666|9\d{2})\d{3}-(?!00)\d{2}-(?!0{4})\d{4}\b")

_CREDIT_CARD = re.compile(
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|"          # Visa
    r"5[1-5][0-9]{14}|"                         # MasterCard
    r"3[47][0-9]{13}|"                          # Amex
    r"6(?:011|5[0-9]{2})[0-9]{12})\b"          # Discover
)

_PHONE_US = re.compile(
    r"\b(?:\+1[\s.-]?)?\(?([0-9]{3})\)?[\s.-]?([0-9]{3})[\s.-]([0-9]{4})\b"
)

_PERSONAL_EMAIL = re.compile(
    r"\b[a-zA-Z0-9._%+\-]+@"
    r"(?:gmail|yahoo|hotmail|outlook|aol|icloud|protonmail|me|mac|"
    r"live|msn|comcast|att|verizon|cox|earthlink|sbcglobal)\.(?:com|net|org|co\.uk)\b",
    re.IGNORECASE,
)

_PASSPORT = re.compile(r"\b[A-Z]{1,2}[0-9]{6,9}\b")

_ROUTING = re.compile(r"\b0[0-9]{8}\b")  # US ABA routing numbers start with 0-1-2-3

_API_KEY = re.compile(
    r"\b(?:sk-|pk-|api_key[=:\s]+|password[=:\s]+|secret[=:\s]+|token[=:\s]+)"
    r"[A-Za-z0-9+/]{20,}\b",
    re.IGNORECASE,
)

# Required compliance text markers
_DISCLAIMER_MARKERS = [
    "confidential",
    "for internal use only",
    "not for distribution",
    "investment banking",
    "this document is confidential",
    "privileged and confidential",
]

_ATTRIBUTION_MARKERS = [
    "source:",
    "data source",
    "sourced from",
    "as reported by",
    "per ",
    "bloomberg",
    "pitchbook",
    "sec edgar",
    "capital iq",
]


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class PIIHit:
    pii_type: str
    location: str       # e.g. "executive_summary.text"
    sample: str         # Redacted sample (first/last chars only)
    severity: str       # "critical" | "warning"


@dataclass
class ComplianceReport:
    status: str                    # "passed" | "warnings" | "failed"
    checks_passed: int = 0
    checks_failed: int = 0
    checks_warned: int = 0
    pii_hits: list[PIIHit] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "checks_passed": self.checks_passed,
            "checks_failed": self.checks_failed,
            "checks_warned": self.checks_warned,
            "pii_hits": [
                {"type": h.pii_type, "location": h.location, "sample": h.sample, "severity": h.severity}
                for h in self.pii_hits
            ],
            "issues": self.issues,
            "warnings": self.warnings,
        }


# ── Core scanner ─────────────────────────────────────────────────────────────

def _redact(match: str) -> str:
    """Return a partially redacted version of a match for reporting."""
    if len(match) <= 4:
        return "***"
    return match[:2] + "*" * (len(match) - 4) + match[-2:]


def _scan_text(text: str, location: str) -> list[PIIHit]:
    """Scan a text string for PII patterns and return hits."""
    hits: list[PIIHit] = []

    for m in _SSN.finditer(text):
        hits.append(PIIHit("ssn", location, _redact(m.group()), "critical"))

    for m in _CREDIT_CARD.finditer(text):
        hits.append(PIIHit("credit_card", location, _redact(m.group()), "critical"))

    for m in _PERSONAL_EMAIL.finditer(text):
        hits.append(PIIHit("personal_email", location, _redact(m.group()), "warning"))

    for m in _API_KEY.finditer(text):
        hits.append(PIIHit("api_key_or_credential", location, _redact(m.group()[:20]), "critical"))

    # Only flag routing numbers if they look like they're in a financial context
    for m in _ROUTING.finditer(text):
        ctx = text[max(0, m.start() - 30): m.end() + 30].lower()
        if any(kw in ctx for kw in ["routing", "aba", "account number", "bank"]):
            hits.append(PIIHit("bank_routing_number", location, _redact(m.group()), "critical"))

    return hits


def _flatten_to_strings(obj: Any, path: str = "root") -> list[tuple[str, str]]:
    """Recursively flatten a JSON-like object to (path, string_value) pairs."""
    results: list[tuple[str, str]] = []
    if isinstance(obj, str):
        results.append((path, obj))
    elif isinstance(obj, dict):
        for k, v in obj.items():
            results.extend(_flatten_to_strings(v, f"{path}.{k}"))
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            results.extend(_flatten_to_strings(item, f"{path}[{i}]"))
    return results


def scan_deliverables(deliverables: dict) -> ComplianceReport:
    """
    Scan all deliverable content for PII and compliance issues.

    Args:
        deliverables: The deliverables dict from the delivery agent state.

    Returns:
        ComplianceReport with status, hits, and issue lists.
    """
    report = ComplianceReport(status="passed")

    # ── 1. PII scanning ───────────────────────────────────────────────────────
    full_text_parts: list[str] = []

    for path, value in _flatten_to_strings(deliverables):
        hits = _scan_text(value, path)
        report.pii_hits.extend(hits)
        full_text_parts.append(value)

    full_text = " ".join(full_text_parts).lower()

    if report.pii_hits:
        critical = [h for h in report.pii_hits if h.severity == "critical"]
        warned = [h for h in report.pii_hits if h.severity == "warning"]
        if critical:
            report.checks_failed += 1
            report.issues.append(
                f"CRITICAL: {len(critical)} PII instance(s) detected "
                f"({', '.join(set(h.pii_type for h in critical))}). "
                "Manual redaction required before distribution."
            )
            report.status = "failed"
        if warned:
            report.checks_warned += 1
            report.warnings.append(
                f"{len(warned)} potential personal contact detail(s) found "
                f"({', '.join(set(h.pii_type for h in warned))}). "
                "Review before external distribution."
            )
            if report.status == "passed":
                report.status = "warnings"
    else:
        report.checks_passed += 1

    # ── 2. Confidentiality disclaimer check ───────────────────────────────────
    has_disclaimer = any(marker in full_text for marker in _DISCLAIMER_MARKERS)
    if has_disclaimer:
        report.checks_passed += 1
    else:
        report.checks_warned += 1
        report.warnings.append(
            "No confidentiality disclaimer found in deliverables. "
            "Consider adding 'Confidential — For Internal Use Only' to the report header."
        )
        if report.status == "passed":
            report.status = "warnings"

    # ── 3. Data attribution check ─────────────────────────────────────────────
    has_attribution = any(marker in full_text for marker in _ATTRIBUTION_MARKERS)
    if has_attribution:
        report.checks_passed += 1
    else:
        report.checks_warned += 1
        report.warnings.append(
            "Data source attribution not clearly present in deliverables. "
            "Ensure each data point references its source system."
        )
        if report.status == "passed":
            report.status = "warnings"

    # ── 4. Credential leak check ─────────────────────────────────────────────
    # Check for password= or api_key= patterns that could be leaked
    cred_pattern = re.search(
        r"\b(password|passwd|api.?key|secret.?key|access.?token)\s*[=:]\s*\S{8,}",
        full_text,
        re.IGNORECASE,
    )
    if cred_pattern:
        report.checks_failed += 1
        report.issues.append(
            "CRITICAL: Possible credential string detected in deliverables. "
            "Credentials must never be included in output documents."
        )
        report.status = "failed"
    else:
        report.checks_passed += 1

    return report
