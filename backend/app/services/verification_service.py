"""
Verification service.

Computes confidence scores for due diligence findings based on corroborating
external records and assesses source independence.
"""

from __future__ import annotations

from typing import Any

# Source systems that are controlled by the seller and thus carry lower weight
SELLER_CONTROLLED: set[str] = {
    "salesforce",
    "netsuite",
    "hubspot",
    "dynamics",
    "quickbooks",
}


def compute_confidence_score(
    findings: list[dict[str, Any]],
    external_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute a confidence score for each finding.

    Scoring rules:
    - Base score: 0.5
    - +0.2 per corroborating external record (keyed on corroborates_finding == finding id)
    - -0.2 if the finding's only source is seller-controlled
    - Capped at [0.0, 1.0]

    Returns a dict with:
        scores: list of {finding_id, title, score, corroborating_records}
        overall: float  — mean of individual scores
    """
    # Build an index: finding_id -> list of corroborating external records
    corroboration_index: dict[str, list[dict[str, Any]]] = {}
    for rec in external_records:
        finding_ref = rec.get("corroborates_finding")
        if finding_ref:
            corroboration_index.setdefault(str(finding_ref), []).append(rec)

    scores: list[dict[str, Any]] = []

    for finding in findings:
        finding_id = str(finding.get("id", ""))
        title = finding.get("title", "")
        source_system = (finding.get("source_system") or "").lower()

        score = 0.5

        # Seller-controlled penalty
        if source_system in SELLER_CONTROLLED:
            supporting = corroboration_index.get(finding_id, [])
            if not supporting:
                score -= 0.2

        # Corroboration bonus
        corroborating = corroboration_index.get(finding_id, [])
        score += 0.2 * len(corroborating)

        # Cap
        score = max(0.0, min(1.0, score))

        scores.append(
            {
                "finding_id": finding_id,
                "title": title,
                "score": round(score, 2),
                "corroborating_records": len(corroborating),
            }
        )

    overall = round(sum(s["score"] for s in scores) / len(scores), 2) if scores else 0.0

    return {
        "scores": scores,
        "overall": overall,
        "total_findings": len(findings),
        "total_external_records": len(external_records),
    }


def compute_source_independence(sources: list[str]) -> float:
    """
    Compute a source independence score in [0.0, 1.0].

    0.0 — all sources are seller-controlled (salesforce, netsuite, hubspot, …)
    1.0 — all sources are external / third-party
    Interpolated for mixed source sets.

    An empty list returns 0.0.
    """
    if not sources:
        return 0.0

    external_count = sum(
        1 for s in sources if s.lower() not in SELLER_CONTROLLED
    )
    return round(external_count / len(sources), 4)
