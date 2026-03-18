"""Contract clause NLP scanner — keyword-based extraction of risky clauses."""
from __future__ import annotations

import re
from typing import Any

CLAUSE_PATTERNS: dict[str, list[str]] = {
    "change_of_control": [
        "change of control",
        "change-of-control",
        "acquisition",
        "merger",
        "assigns",
        "assignable without consent",
        "consent required",
        "successor",
    ],
    "ip_ownership": [
        "intellectual property",
        "work for hire",
        "work-for-hire",
        "assigns all right",
        "invention assignment",
        "proprietary rights",
        "all inventions",
        "moral rights waived",
    ],
    "non_compete": [
        "non-compete",
        "non compete",
        "noncompete",
        "covenant not to compete",
        "competitive activity",
        "competitive business",
        "restrict.*compet",
    ],
    "litigation": [
        "whereas",
        "plaintiff",
        "defendant",
        "in the matter of",
        "lawsuit",
        "settlement",
        "damages",
        "arbitration",
        "mediation",
        "court of",
        "tribunal",
    ],
    "regulatory": [
        r"\bfda\b",
        r"\bsec\b",
        r"\bhipaa\b",
        r"\bgdpr\b",
        r"\bpci\b",
        r"\bsox\b",
        "compliance",
        "regulatory approval",
        "regulatory requirement",
    ],
}

RISK_MAP = {
    "change_of_control": "critical",
    "ip_ownership": "critical",
    "non_compete": "warning",
    "litigation": "warning",
    "regulatory": "info",
}

_DATE_RE = re.compile(
    r"\b(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4}|\w+ \d{1,2},? \d{4}|\d{4}[/\-]\d{2}[/\-]\d{2})\b"
)


def analyze_contract(
    text: str, document_id: str, engagement_id: str
) -> list[dict[str, Any]]:
    """Scan text for clause patterns. Returns list of finding dicts."""
    if not text:
        return []
    findings: list[dict[str, Any]] = []
    lower = text.lower()
    for clause_type, patterns in CLAUSE_PATTERNS.items():
        for pattern in patterns:
            match = re.search(pattern, lower)
            if match:
                start = max(0, match.start() - 60)
                end = min(len(text), match.end() + 60)
                excerpt = text[start:end].strip().replace("\n", " ")
                findings.append(
                    {
                        "clause_type": clause_type,
                        "text_excerpt": excerpt[:300],
                        "risk_level": RISK_MAP.get(clause_type, "info"),
                        "requires_review": RISK_MAP.get(clause_type, "info")
                        in ("critical", "warning"),
                        "document_id": document_id,
                        "engagement_id": engagement_id,
                    }
                )
                break  # one finding per clause type per document
    return findings


def extract_key_dates(text: str) -> list[dict[str, str]]:
    results = []
    for match in _DATE_RE.finditer(text):
        start = max(0, match.start() - 40)
        end = min(len(text), match.end() + 40)
        context = text[start:end].strip().replace("\n", " ")
        results.append({"date_str": match.group(0), "context": context})
    return results[:20]


def score_contract_risk(findings: list[dict]) -> dict[str, Any]:
    critical = sum(1 for f in findings if f.get("risk_level") == "critical")
    warning = sum(1 for f in findings if f.get("risk_level") == "warning")
    if critical > 0:
        overall = "critical"
    elif warning > 0:
        overall = "high"
    elif findings:
        overall = "medium"
    else:
        overall = "low"
    return {
        "overall_risk": overall,
        "critical_count": critical,
        "warning_count": warning,
        "info_count": len(findings) - critical - warning,
        "summary": f"{len(findings)} clause(s) flagged: {critical} critical, {warning} warning",
    }
