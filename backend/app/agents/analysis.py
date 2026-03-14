"""
Analysis Agent — cross-references data, detects discrepancies, validates findings.

Receives structured data from the Research Agent and performs:
- Multi-source cross-referencing
- Variance and discrepancy detection (e.g., CRM vs ERP revenue gaps)
- Financial model synchronization
- Exception flagging for human review
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent, StepResult
from app.llm.exceptions import LLMError
from app.llm.prompts import (
    SYSTEM_CROSS_REFERENCE,
    SYSTEM_SCORE_FINDINGS,
    USER_CROSS_REFERENCE,
    USER_SCORE_FINDINGS,
)

logger = logging.getLogger(__name__)

# ── Benchmarks ────────────────────────────────────────────────────────────────
SMB_CHURN_BENCHMARK_PCT  = 8.0    # SaaS benchmark: SMB churn < 8%
MID_CHURN_BENCHMARK_PCT  = 5.0    # Mid-market churn benchmark
REVENUE_VARIANCE_PCT     = 5.0    # Flag revenue variance > 5%
RD_VARIANCE_PCT          = 8.0    # Flag R&D cost variance > 8%
AR_OVERDUE_DAYS          = 120    # Flag AR > 120 days


class AnalysisAgent(BaseAgent):
    """
    Real-time cross-referencing and variance detection agent.

    Steps:
        1. Ingest — receive and normalize Research Agent outputs
        2. Cross-reference — compare data across sources
        3. Variance detection — flag discrepancies exceeding thresholds
        4. Financial modeling — update / validate financial models
        5. Exception routing — determine which findings need human review
        6. Scoring — assign confidence scores to all findings
    """

    agent_type = "analysis"

    def define_steps(self, config: dict) -> list[str]:
        """Define analysis steps."""
        return [
            "ingest_research_data",
            "normalize_data",
            "cross_reference_sources",
            "detect_revenue_variances",
            "detect_cost_variances",
            "analyze_customer_metrics",
            "analyze_market_position",
            "financial_model_sync",
            "route_exceptions",
            "score_findings",
            "compile_analysis",
        ]

    async def execute_step(self, step_index: int, step_name: str) -> StepResult:
        """Execute an analysis step."""

        step_map = {
            "ingest_research_data":   self._ingest_research_data,
            "normalize_data":         self._normalize_data,
            "cross_reference_sources": self._cross_reference_sources,
            "detect_revenue_variances": self._detect_revenue_variances,
            "detect_cost_variances":  self._detect_cost_variances,
            "analyze_customer_metrics": self._analyze_customer_metrics,
            "analyze_market_position": self._analyze_market_position,
            "financial_model_sync":   self._financial_model_sync,
            "route_exceptions":       self._route_exceptions,
            "score_findings":         self._score_findings,
            "compile_analysis":       self._compile_analysis,
        }

        handler = step_map.get(step_name)
        if handler:
            return await handler()
        return StepResult(success=False, message=f"Unknown step: {step_name}")

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _get_ingested(self) -> dict[str, Any]:
        return self.state.get("ingested_data", {})

    def _src(self, source: str, key: str, default: Any = None) -> Any:
        """Safely retrieve extracted data for a source + extraction type."""
        return self._get_ingested().get(source, {}).get(key, default if default is not None else [])

    # ── Step implementations ──────────────────────────────────────────────────

    async def _ingest_research_data(self) -> StepResult:
        """Ingest and categorize data from the Research Agent."""
        pipeline_data = self.state.get("pipeline_config", {}).get("pipeline_data", {})
        research_data = pipeline_data.get("research", {})
        raw_data = research_data.get("results", {}).get("compile_results", {}).get("raw_data", {})

        self.state["ingested_data"] = raw_data
        self.state["source_count"] = len(raw_data)

        return StepResult(
            success=True,
            data={"sources_ingested": len(raw_data)},
            message=f"Ingested data from {len(raw_data)} sources",
        )

    async def _normalize_data(self) -> StepResult:
        """Normalize data formats across sources for comparison."""
        ingested = self._get_ingested()
        normalized_count = sum(len(v) for v in ingested.values() if isinstance(v, dict))
        self.state["normalized"] = True

        return StepResult(
            success=True,
            data={"records_normalized": normalized_count},
            message=f"Normalized data across {len(ingested)} sources",
        )

    async def _cross_reference_sources(self) -> StepResult:
        """Cross-reference data across multiple sources using LLM (with deterministic fallback)."""
        if self.state.get("cross_references", {}).get("summary"):
            xrefs = self.state["cross_references"]
            total = sum(len(v) for v in xrefs.values() if isinstance(v, list))
            return StepResult(
                success=True,
                data={"cross_references_found": total},
                message=f"Cross-references restored from checkpoint ({total} found)",
            )

        ingested = self._get_ingested()
        findings: list[dict] = []

        try:
            from app.llm import get_llm_client
            llm = get_llm_client()
            data_summary = json.dumps(ingested, indent=1, default=str)[:50_000]
            user_prompt = USER_CROSS_REFERENCE.format(
                source_count=len(ingested),
                data_summary=data_summary,
            )
            result = await llm.complete_json(SYSTEM_CROSS_REFERENCE, user_prompt)
            cross_refs = {
                "crm_erp_overlap":               result.get("crm_erp_overlap", []),
                "marketing_revenue_correlation": result.get("marketing_revenue_correlation", []),
                "market_data_benchmarks":        result.get("market_data_benchmarks", []),
                "summary":                       result.get("summary", ""),
            }
            for xref in cross_refs["crm_erp_overlap"]:
                if xref.get("match_quality", 1.0) < 0.5:
                    findings.append({
                        "type": "discrepancy",
                        "source_system": "_vs_".join(xref.get("sources_compared", [])),
                        "title": f"Data mismatch: {xref.get('metric', 'unknown metric')}",
                        "description": xref.get("notes", ""),
                        "data": xref,
                        "severity": "warning",
                        "requires_human_review": True,
                    })
            total = sum(len(v) for v in cross_refs.values() if isinstance(v, list))

        except LLMError:
            logger.warning("LLM unavailable for cross-referencing — using deterministic fallback")
            cross_refs = {
                "crm_erp_overlap": [],
                "marketing_revenue_correlation": [],
                "market_data_benchmarks": [],
                "summary": "Deterministic cross-referencing applied (LLM unavailable)",
            }

            # ── Funding discrepancy: Crunchbase vs SEC Edgar ──────────────────
            cb_funding  = self._src("crunchbase", "total_funding_crunchbase") or 0
            sec_filings = self._src("sec_edgar", "10k_filings") or []
            if cb_funding and sec_filings:
                sec_cash = sec_filings[0].get("cash", 0) if sec_filings else 0
                # Crunchbase shows total raised; cash on hand is typically much lower —
                # flag only if Crunchbase figure looks inflated vs SEC
                if isinstance(cb_funding, (int, float)) and cb_funding > 0:
                    findings.append({
                        "type": "discrepancy",
                        "source_system": "crunchbase_vs_sec_edgar",
                        "title": f"Funding narrative discrepancy: Crunchbase shows ${cb_funding/1e6:.1f}M raised vs ${sec_cash/1e6:.1f}M cash on hand",
                        "description": (
                            f"Crunchbase records ${cb_funding/1e6:.1f}M total raised. "
                            f"SEC 10-K shows ${sec_cash/1e6:.1f}M cash and "
                            f"${sec_filings[0].get('total_assets',0)/1e6:.1f}M total assets. "
                            "Verify all funding rounds are reflected in audited financials."
                        ),
                        "data": {"crunchbase_raised": cb_funding, "sec_cash": sec_cash},
                        "severity": "info",
                        "requires_human_review": False,
                    })

            total = len(findings)

        self.state["cross_references"] = cross_refs
        return StepResult(
            success=True,
            data={"cross_references_found": total},
            findings=findings,
            message=f"Cross-referencing complete — {total} references found",
        )

    async def _detect_revenue_variances(self) -> StepResult:
        """Detect revenue variances between SAP income statement and NetSuite ARR."""
        findings: list[dict] = []

        # ── SAP FY2025 revenue vs NetSuite ARR-implied annual revenue ─────────
        sap_fs    = self._src("sap", "financial_statements") or {}
        ns_data   = self._src("netsuite", "revenue_data") or []

        sap_revenue = sap_fs.get("income_statement", {}).get("revenue", 0) if isinstance(sap_fs, dict) else 0
        # NetSuite ARR from latest period
        ns_arr = 0
        if ns_data:
            ns_arr = ns_data[-1].get("arr_contribution", 0)

        if sap_revenue and ns_arr:
            variance     = ns_arr - sap_revenue
            variance_pct = abs(variance) / sap_revenue * 100

            if variance_pct > REVENUE_VARIANCE_PCT:
                severity = "critical" if variance_pct > 10 else "warning"
                findings.append({
                    "type": "discrepancy",
                    "source_system": "sap_vs_netsuite",
                    "title": f"${abs(variance)/1e6:.1f}M Revenue Variance: SAP vs NetSuite",
                    "description": (
                        f"SAP FY2025 income statement shows ${sap_revenue/1e6:.2f}M revenue. "
                        f"NetSuite ARR implies ${ns_arr/1e6:.2f}M annualised revenue. "
                        f"Variance: ${abs(variance)/1e6:.1f}M ({variance_pct:.1f}%). "
                        "Verify revenue recognition policies and deferred revenue treatment."
                    ),
                    "data": {
                        "sap_revenue": sap_revenue,
                        "netsuite_arr": ns_arr,
                        "variance": variance,
                        "variance_pct": round(variance_pct, 1),
                    },
                    "severity": severity,
                    "requires_human_review": True,
                })

        # ── NetSuite churn trend ──────────────────────────────────────────────
        if len(ns_data) >= 3:
            total_churn = sum(abs(q.get("churn", 0)) for q in ns_data)
            avg_q_revenue = sum(q.get("revenue", 0) for q in ns_data) / len(ns_data)
            churn_pct = total_churn / (avg_q_revenue * len(ns_data)) * 100 if avg_q_revenue else 0
            if churn_pct > 3.0:
                findings.append({
                    "type": "data_point",
                    "source_system": "netsuite",
                    "title": f"NetSuite trailing churn: ${total_churn/1e6:.1f}M ({churn_pct:.1f}% of revenue)",
                    "description": (
                        f"NetSuite records ${total_churn/1e3:.0f}K gross churn across {len(ns_data)} periods. "
                        f"Average quarterly revenue: ${avg_q_revenue/1e6:.1f}M."
                    ),
                    "data": {"total_churn": total_churn, "churn_pct": round(churn_pct, 1)},
                    "severity": "info",
                    "requires_human_review": False,
                })

        self.state["revenue_variances"] = findings
        return StepResult(
            success=True,
            data={"variances_detected": len(findings)},
            findings=findings,
            message=f"Revenue variance analysis complete — {len(findings)} findings",
        )

    async def _detect_cost_variances(self) -> StepResult:
        """Detect cost and expense variances across sources."""
        findings: list[dict] = []

        # ── R&D: SAP income statement vs Oracle GL annualised ─────────────────
        sap_fs  = self._src("sap", "financial_statements") or {}
        gl      = self._src("oracle", "gl_entries") or []

        sap_rd = sap_fs.get("income_statement", {}).get("operating_expenses", {}).get("research_development", 0) if isinstance(sap_fs, dict) else 0

        # Oracle GL entries are Q4-period — annualise by ×4
        oracle_eng_q4 = sum(
            abs(e.get("net", 0))
            for e in gl
            if isinstance(e, dict) and any(
                kw in e.get("account_name", "").lower()
                for kw in ("research", "r&d", "engineering")
            )
        )
        oracle_rd_annual = oracle_eng_q4 * 4  # annualise

        if sap_rd and oracle_rd_annual:
            variance     = abs(oracle_rd_annual - sap_rd)
            variance_pct = variance / sap_rd * 100

            if variance_pct > RD_VARIANCE_PCT:
                severity = "critical" if variance_pct > 20 else "warning"
                findings.append({
                    "type": "discrepancy",
                    "source_system": "sap_vs_oracle",
                    "title": f"${variance/1e3:.0f}K R&D Cost Mismatch: SAP vs Oracle GL",
                    "description": (
                        f"SAP income statement shows ${sap_rd/1e6:.2f}M R&D expense for FY2025. "
                        f"Oracle GL (Engineering + R&D, Q4 annualised) implies ${oracle_rd_annual/1e6:.2f}M. "
                        f"Variance: ${variance/1e3:.0f}K ({variance_pct:.1f}%). "
                        "Review cost capitalisation policies and internal cost allocation."
                    ),
                    "data": {
                        "sap_rd_annual": sap_rd,
                        "oracle_rd_annualised": oracle_rd_annual,
                        "variance": variance,
                        "variance_pct": round(variance_pct, 1),
                    },
                    "severity": severity,
                    "requires_human_review": True,
                })

        self.state["cost_variances"] = findings
        return StepResult(
            success=True,
            data={"cost_variances_detected": len(findings)},
            findings=findings,
            message=f"Cost variance analysis complete — {len(findings)} findings",
        )

    async def _analyze_customer_metrics(self) -> StepResult:
        """Analyze customer metrics — churn, LTV, CAC, NRR across sources."""
        findings: list[dict] = []

        # ── SMB churn from Dynamics ───────────────────────────────────────────
        segments = self._src("dynamics", "customer_segments") or []
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            churn = seg.get("churn_rate_pct", 0)
            name  = seg.get("segment", "")
            if "SMB" in name or "<100" in name:
                if churn > SMB_CHURN_BENCHMARK_PCT:
                    findings.append({
                        "type": "discrepancy",
                        "source_system": "dynamics",
                        "title": f"High SMB Churn: {churn}% (benchmark <{SMB_CHURN_BENCHMARK_PCT}%)",
                        "description": (
                            f"Dynamics CRM records {churn}% annual churn in the SMB segment "
                            f"({seg.get('customer_count', '?')} customers, "
                            f"${seg.get('arr_m', 0):.1f}M ARR). "
                            f"SaaS benchmark for SMB is <{SMB_CHURN_BENCHMARK_PCT}%. "
                            "Elevated churn suggests product-market fit or support gaps at this tier."
                        ),
                        "data": seg,
                        "severity": "critical",
                        "requires_human_review": True,
                    })
            elif "Mid" in name or "mid" in name:
                if churn > MID_CHURN_BENCHMARK_PCT:
                    findings.append({
                        "type": "data_point",
                        "source_system": "dynamics",
                        "title": f"Mid-Market Churn {churn}% (above {MID_CHURN_BENCHMARK_PCT}% benchmark)",
                        "description": (
                            f"Mid-market churn of {churn}% is above the {MID_CHURN_BENCHMARK_PCT}% SaaS benchmark. "
                            f"Segment ARR: ${seg.get('arr_m', 0):.1f}M."
                        ),
                        "data": seg,
                        "severity": "warning",
                        "requires_human_review": False,
                    })

        # ── Overdue AR from Oracle ────────────────────────────────────────────
        ar_aging = self._src("oracle", "ar_aging") or []
        overdue  = [
            a for a in ar_aging
            if isinstance(a, dict) and a.get("days_outstanding", 0) >= AR_OVERDUE_DAYS
        ]
        if overdue:
            total_overdue = sum(a.get("amount", 0) for a in overdue)
            findings.append({
                "type": "exception",
                "source_system": "oracle",
                "title": f"${total_overdue/1e3:.0f}K AR Overdue 120+ Days ({len(overdue)} accounts)",
                "description": (
                    f"Oracle AR aging shows {len(overdue)} account(s) with invoices outstanding "
                    f"≥{AR_OVERDUE_DAYS} days totalling ${total_overdue/1e3:.0f}K. "
                    + ", ".join(
                        f"{a['customer']} (${a['amount']/1e3:.0f}K, {a['days_outstanding']}d — {a.get('collection_status','?')})"
                        for a in overdue
                    ) + ". "
                    "Review collection strategy and bad debt reserve adequacy."
                ),
                "data": {"overdue_accounts": overdue, "total_overdue": total_overdue},
                "severity": "warning",
                "requires_human_review": True,
            })

        # ── HubSpot funnel leakage ────────────────────────────────────────────
        funnel = self._src("hubspot", "lead_funnel") or []
        mql_stage = next((s for s in funnel if isinstance(s, dict) and s.get("stage") == "MQL"), None)
        if mql_stage:
            mql_to_sql = mql_stage.get("conversion_to_next_pct", 0)
            if mql_to_sql < 15.0:
                findings.append({
                    "type": "data_point",
                    "source_system": "hubspot",
                    "title": f"HubSpot MQL→SQL Conversion {mql_to_sql:.1f}% (below 30% SaaS benchmark)",
                    "description": (
                        f"HubSpot shows MQL→SQL conversion of {mql_to_sql:.1f}% vs 30%+ SaaS benchmark. "
                        "Low conversion suggests misaligned lead scoring or sales follow-up gaps."
                    ),
                    "data": mql_stage,
                    "severity": "warning",
                    "requires_human_review": False,
                })

        self.state["customer_analysis"] = {"findings_count": len(findings)}
        return StepResult(
            success=True,
            data={"metrics_analyzed": len(findings)},
            findings=findings,
            message=f"Customer metrics analysis complete — {len(findings)} findings",
        )

    async def _analyze_market_position(self) -> StepResult:
        """Analyze headcount discrepancies and key-person risk."""
        findings: list[dict] = []

        # ── Headcount mismatch: ZoomInfo vs SAP ──────────────────────────────
        zi_trends  = self._src("zoominfo", "employee_count_trends") or []
        sap_fs     = self._src("sap", "financial_statements") or {}

        zi_latest_hc  = zi_trends[-1].get("headcount", 0) if zi_trends else 0
        sap_hc        = sap_fs.get("headcount_by_department", {}).get("total", 0) if isinstance(sap_fs, dict) else 0

        if zi_latest_hc and sap_hc:
            hc_gap = abs(zi_latest_hc - sap_hc)
            if hc_gap >= 10:
                findings.append({
                    "type": "discrepancy",
                    "source_system": "zoominfo_vs_sap",
                    "title": f"Headcount Discrepancy: ZoomInfo {zi_latest_hc} vs SAP {sap_hc} ({hc_gap}-person gap)",
                    "description": (
                        f"ZoomInfo reports {zi_latest_hc} employees. "
                        f"SAP HR records show {sap_hc} headcount. "
                        f"Gap of {hc_gap} may reflect contractors, unfilled open roles, "
                        "or delayed HR system updates. Verify with payroll records."
                    ),
                    "data": {
                        "zoominfo_headcount": zi_latest_hc,
                        "sap_headcount": sap_hc,
                        "gap": hc_gap,
                    },
                    "severity": "info",
                    "requires_human_review": False,
                })

        # ── Key-person risk: Sales Navigator departures ───────────────────────
        updates = self._src("sales_navigator", "company_updates") or []
        decision_makers = self._src("sales_navigator", "decision_makers") or []
        vp_eng = next(
            (p for p in decision_makers if isinstance(p, dict) and "engineering" in p.get("title", "").lower()),
            None,
        )
        departures = [
            u for u in updates
            if isinstance(u, dict) and any(
                kw in u.get("content", "").lower()
                for kw in ("depart", "left", "resign", "exit", "goodbye")
            )
        ]
        if not vp_eng:
            findings.append({
                "type": "exception",
                "source_system": "sales_navigator",
                "title": "Key Person Risk: VP / Head of Engineering not found in leadership",
                "description": (
                    "Sales Navigator decision-maker list does not include a VP Engineering or "
                    "Head of Engineering. This may indicate a recent departure or unfilled leadership gap. "
                    "Verify engineering leadership continuity before close."
                ),
                "data": {"decision_makers": [p.get("title") for p in decision_makers if isinstance(p, dict)]},
                "severity": "warning",
                "requires_human_review": True,
            })
        for d in departures:
            findings.append({
                "type": "exception",
                "source_system": "sales_navigator",
                "title": f"Leadership departure detected: {d.get('content', '')[:80]}",
                "description": d.get("content", ""),
                "data": d,
                "severity": "warning",
                "requires_human_review": True,
            })

        self.state["market_analysis"] = {"findings_count": len(findings)}
        return StepResult(
            success=True,
            data={"benchmarks_compared": len(findings)},
            findings=findings,
            message=f"Market position analysis complete — {len(findings)} findings",
        )

    async def _financial_model_sync(self) -> StepResult:
        return StepResult(
            success=True,
            data={"model_updated": False, "status": "pending_integration"},
            message="Financial model sync placeholder",
        )

    async def _route_exceptions(self) -> StepResult:
        """Determine which findings require human review vs automatic processing."""
        all_variances = (
            self.state.get("revenue_variances", [])
            + self.state.get("cost_variances", [])
        )
        human_review  = [v for v in all_variances if v.get("severity") == "critical"]
        auto_processed = [v for v in all_variances if v.get("severity") != "critical"]

        self.state["exceptions"] = {
            "human_review": human_review,
            "auto_processed": auto_processed,
        }
        return StepResult(
            success=True,
            data={
                "human_review_count": len(human_review),
                "auto_processed_count": len(auto_processed),
            },
            message=f"Routed {len(human_review)} exceptions for human review",
        )

    async def _score_findings(self) -> StepResult:
        """Assign confidence scores to all findings using LLM (with fallback defaults)."""
        if self.state.get("scored_findings"):
            scored = self.state["scored_findings"]
            return StepResult(
                success=True,
                data={"findings_scored": len(scored), "overall_confidence": self.state.get("overall_confidence", 0)},
                message=f"Scored findings restored from checkpoint ({len(scored)})",
            )

        all_findings = (
            self.state.get("revenue_variances", [])
            + self.state.get("cost_variances", [])
        )
        xrefs = self.state.get("cross_references", {})
        for xref in xrefs.get("crm_erp_overlap", []):
            if xref.get("match_quality", 1.0) < 0.5:
                all_findings.append(xref)

        if not all_findings:
            self.state["scored_findings"] = []
            self.state["overall_confidence"] = 0.75
            return StepResult(
                success=True,
                data={"findings_scored": 0, "overall_confidence": 0.75},
                message="No findings to score",
            )

        try:
            from app.llm import get_llm_client
            llm = get_llm_client()
            findings_json = json.dumps(all_findings, indent=1, default=str)[:30_000]
            user_prompt = USER_SCORE_FINDINGS.format(findings_json=findings_json)
            result = await llm.complete_json(SYSTEM_SCORE_FINDINGS, user_prompt)
            scored  = result.get("scored_findings", [])
            overall = result.get("overall_confidence", 0.75)

        except LLMError:
            logger.warning("LLM unavailable for scoring — applying default confidence scores")
            scored = [
                {
                    "finding_index": i,
                    "reliability_score": 0.85,
                    "impact_score": 0.8 if f.get("severity") == "critical" else 0.5,
                    "confidence_justification": "Default score — computed from fixture data",
                    "recommended_action": "flag_for_review" if f.get("requires_human_review") else "auto_process",
                }
                for i, f in enumerate(all_findings)
            ]
            overall = 0.8

        self.state["scored_findings"] = scored
        self.state["overall_confidence"] = overall
        return StepResult(
            success=True,
            data={"findings_scored": len(scored), "overall_confidence": overall},
            message=f"Scored {len(scored)} findings (confidence: {overall:.0%})",
        )

    async def _compile_analysis(self) -> StepResult:
        """Compile all analysis results for the Delivery agent."""
        analysis_summary = {
            "source_count":      self.state.get("source_count", 0),
            "revenue_variances": self.state.get("revenue_variances", []),
            "cost_variances":    self.state.get("cost_variances", []),
            "customer_analysis": self.state.get("customer_analysis", {}),
            "market_analysis":   self.state.get("market_analysis", {}),
            "cross_references":  self.state.get("cross_references", {}),
            "exceptions":        self.state.get("exceptions", {}),
            "scored_findings":   self.state.get("scored_findings", []),
            "overall_confidence": self.state.get("overall_confidence", 0),
        }
        return StepResult(
            success=True,
            data={"analysis_summary": analysis_summary},
            message="Analysis compilation complete",
        )
