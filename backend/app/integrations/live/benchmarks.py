"""
Deal benchmarking — aggregate comparable transaction data.

Combines Crunchbase (live REST) and PitchBook (TinyFish browser automation)
to build a benchmark dataset of comparable SaaS M&A transactions.

Used by the Analysis Agent's `benchmark_metrics` step to contextualise
the target's ARR growth, NRR, churn, and gross margin against deal comps.
"""

from __future__ import annotations

import logging
import math
import statistics
from typing import Any

logger = logging.getLogger(__name__)


def _safe_percentile(data: list[float], p: float) -> float | None:
    """Return the p-th percentile of a sorted list, or None if empty."""
    if not data:
        return None
    sorted_data = sorted(data)
    n = len(sorted_data)
    idx = (p / 100) * (n - 1)
    lower = math.floor(idx)
    upper = math.ceil(idx)
    if lower == upper:
        return sorted_data[lower]
    return sorted_data[lower] + (sorted_data[upper] - sorted_data[lower]) * (idx - lower)


class BenchmarkAggregator:
    """
    Aggregates comparable transaction data from Crunchbase and PitchBook
    to produce benchmark statistics for the target company.
    """

    def __init__(self, company_name: str, sector: str | None = None) -> None:
        self.company_name = company_name
        self.sector = sector or "SaaS"

    def compute_benchmarks(
        self, deal_comps: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Compute benchmark statistics from a list of comparable M&A deals.

        Each deal comp should have: ev_revenue, growth_pct, ev_arr (optional),
        gross_margin (optional), nrr (optional), churn_pct (optional).

        Returns a summary dict with median, mean, percentiles per metric.
        """
        if not deal_comps:
            return {"error": "No comparable transactions available", "sample_size": 0}

        ev_revenue = [d["ev_revenue"] for d in deal_comps if d.get("ev_revenue") is not None]
        growth_pcts = [d["growth_pct"] for d in deal_comps if d.get("growth_pct") is not None]
        ev_arrs = [d["ev_arr"] for d in deal_comps if d.get("ev_arr") is not None]
        gross_margins = [d["gross_margin"] for d in deal_comps if d.get("gross_margin") is not None]
        nrrs = [d["nrr"] for d in deal_comps if d.get("nrr") is not None]

        def stats(values: list[float]) -> dict[str, float | None]:
            if not values:
                return {"median": None, "mean": None, "p25": None, "p75": None}
            return {
                "median": statistics.median(values),
                "mean": statistics.mean(values),
                "p25": _safe_percentile(values, 25),
                "p75": _safe_percentile(values, 75),
                "sample": len(values),
            }

        result: dict[str, Any] = {
            "sample_size": len(deal_comps),
            "sector": self.sector,
            "ev_revenue": stats(ev_revenue),
            "ev_arr": stats(ev_arrs),
            "revenue_growth_pct": stats(growth_pcts),
            "gross_margin_pct": stats(gross_margins),
            "nrr_pct": stats(nrrs),
            "comps": [
                {
                    "target": d.get("target"),
                    "acquirer": d.get("acquirer"),
                    "deal_date": d.get("deal_date"),
                    "deal_value_m": d.get("deal_value_m"),
                    "ev_revenue": d.get("ev_revenue"),
                    "growth_pct": d.get("growth_pct"),
                }
                for d in deal_comps[:10]  # include top 10 comps in output
            ],
        }

        logger.info(
            "Benchmarks computed for '%s': %d comps, EV/Rev median=%.1fx",
            self.company_name,
            len(deal_comps),
            result["ev_revenue"].get("median") or 0,
        )
        return result

    def compare_target(
        self,
        target_metrics: dict[str, float | None],
        benchmarks: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """
        Compare target company metrics against benchmarks.

        target_metrics keys: ev_revenue, growth_pct, gross_margin, nrr, churn_pct
        Returns list of comparison findings:
        {metric, target_value, benchmark_median, percentile_rank, flag (above/below/in_range)}
        """
        findings = []
        metric_map = [
            ("ev_revenue", "EV / Revenue multiple", benchmarks.get("ev_revenue", {})),
            ("growth_pct", "Revenue growth (%)", benchmarks.get("revenue_growth_pct", {})),
            ("gross_margin", "Gross margin (%)", benchmarks.get("gross_margin_pct", {})),
            ("nrr", "Net Revenue Retention (%)", benchmarks.get("nrr_pct", {})),
        ]

        for key, label, bench in metric_map:
            target_val = target_metrics.get(key)
            median = bench.get("median")
            p25 = bench.get("p25")
            p75 = bench.get("p75")

            if target_val is None or median is None:
                continue

            if p25 and target_val < p25:
                flag = "below_p25"
            elif p75 and target_val > p75:
                flag = "above_p75"
            else:
                flag = "in_range"

            findings.append({
                "metric": label,
                "key": key,
                "target_value": target_val,
                "benchmark_median": median,
                "benchmark_p25": p25,
                "benchmark_p75": p75,
                "delta_vs_median": round(target_val - median, 2),
                "flag": flag,
            })

        return findings
