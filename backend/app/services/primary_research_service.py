"""
Primary research service.

Provides keyword-based theme extraction, sentiment inference,
and interview summary aggregation for commercial due diligence.
"""

from __future__ import annotations

import re
from collections import Counter
from typing import Any


# ── Theme extraction ──────────────────────────────────────────────────────────

_THEME_KEYWORDS: dict[str, list[str]] = {
    "competition": ["compet", "rival", "market share", "disrupt", "alternative"],
    "pricing": ["pric", "discount", "margin", "cost", "expensive", "cheap"],
    "churn": ["churn", "attrition", "cancel", "retention", "lost customer", "leave"],
    "growth": ["growth", "expand", "scale", "increase", "revenue", "upsell", "acquisition"],
    "risk": ["risk", "concern", "issue", "problem", "challenge", "uncertain", "regulatory"],
    "positive": ["great", "excellent", "strong", "impres", "love", "recommend", "best"],
    "strong": ["robust", "solid", "reliable", "durable", "stable", "dominant"],
}


def extract_themes(notes: str) -> list[str]:
    """
    Extract key themes from interview notes using keyword matching.

    Returns a deduplicated list of theme labels found in the text,
    ordered by first appearance.
    """
    if not notes:
        return []

    lower = notes.lower()
    found: list[str] = []

    for theme, keywords in _THEME_KEYWORDS.items():
        for kw in keywords:
            if kw in lower:
                if theme not in found:
                    found.append(theme)
                break

    return found


# ── Sentiment inference ───────────────────────────────────────────────────────

_POSITIVE_SIGNALS = [
    "great", "excellent", "impres", "love", "recommend", "best", "strong",
    "positive", "happy", "satisfied", "outperform", "leader", "solid",
    "robust", "reliable", "grow", "success",
]

_NEGATIVE_SIGNALS = [
    "concern", "issue", "problem", "risk", "poor", "fail", "disappoint",
    "churn", "cancel", "lose", "lost", "difficult", "challenge", "weak",
    "decline", "drop", "behind", "lag", "complain", "bug", "error",
    "expensive", "overpriced", "slow", "unreliable",
]


def infer_sentiment(notes: str) -> str:
    """
    Infer sentiment from interview notes using keyword counting.

    Returns 'positive', 'negative', or 'neutral'.
    """
    if not notes:
        return "neutral"

    lower = notes.lower()

    pos_count = sum(1 for kw in _POSITIVE_SIGNALS if kw in lower)
    neg_count = sum(1 for kw in _NEGATIVE_SIGNALS if kw in lower)

    if pos_count > neg_count:
        return "positive"
    if neg_count > pos_count:
        return "negative"
    return "neutral"


# ── Interview summary aggregation ─────────────────────────────────────────────

def summarize_interviews(records: list[Any]) -> dict[str, Any]:
    """
    Aggregate primary research records into a summary dict.

    Accepts ORM model instances or plain dicts; accesses fields via
    getattr (ORM) or dict .get() transparently.

    Returns:
        total: int
        by_type: dict[str, int]
        sentiment_distribution: dict[str, int]
        top_themes: list[str]  — up to 5 most common themes
        companies_covered: list[str]
    """

    def _get(obj: Any, field: str) -> Any:
        if isinstance(obj, dict):
            return obj.get(field)
        return getattr(obj, field, None)

    total = len(records)
    by_type: Counter[str] = Counter()
    sentiment_dist: Counter[str] = Counter()
    theme_counter: Counter[str] = Counter()
    companies: list[str] = []

    for rec in records:
        rec_type = _get(rec, "type")
        if rec_type is not None:
            # Handle both enum instances and raw strings
            type_val = rec_type.value if hasattr(rec_type, "value") else str(rec_type)
            by_type[type_val] += 1

        sentiment = _get(rec, "sentiment") or "neutral"
        sentiment_dist[sentiment] += 1

        themes = _get(rec, "key_themes") or []
        for theme in themes:
            theme_counter[theme] += 1

        company = _get(rec, "company_name")
        if company and company not in companies:
            companies.append(company)

    top_themes = [theme for theme, _ in theme_counter.most_common(5)]

    return {
        "total": total,
        "by_type": dict(by_type),
        "sentiment_distribution": dict(sentiment_dist),
        "top_themes": top_themes,
        "companies_covered": companies,
    }
