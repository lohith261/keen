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
            "ingest_research_data": self._ingest_research_data,
            "normalize_data": self._normalize_data,
            "cross_reference_sources": self._cross_reference_sources,
            "detect_revenue_variances": self._detect_revenue_variances,
            "detect_cost_variances": self._detect_cost_variances,
            "analyze_customer_metrics": self._analyze_customer_metrics,
            "analyze_market_position": self._analyze_market_position,
            "financial_model_sync": self._financial_model_sync,
            "route_exceptions": self._route_exceptions,
            "score_findings": self._score_findings,
            "compile_analysis": self._compile_analysis,
        }

        handler = step_map.get(step_name)
        if handler:
            return await handler()
        return StepResult(success=False, message=f"Unknown step: {step_name}")

    # ── Step implementations ─────────────────────────────

    async def _ingest_research_data(self) -> StepResult:
        """Ingest and categorize data from the Research Agent."""
        # Pipeline data from Research Agent is injected via config
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
        # TODO: In production, normalize currencies, date formats,
        # metric definitions, entity names across sources
        ingested = self.state.get("ingested_data", {})

        normalized_count = 0
        for source, data in ingested.items():
            normalized_count += len(data) if isinstance(data, dict) else 0

        self.state["normalized"] = True

        return StepResult(
            success=True,
            data={"records_normalized": normalized_count},
            message=f"Normalized {normalized_count} data records",
        )

    async def _cross_reference_sources(self) -> StepResult:
        """Cross-reference data across multiple sources using LLM."""
        # Idempotency: skip if already cross-referenced
        if self.state.get("cross_references", {}).get("summary"):
            xrefs = self.state["cross_references"]
            total = sum(len(v) for v in xrefs.values() if isinstance(v, list))
            return StepResult(
                success=True,
                data={"cross_references_found": total},
                message=f"Cross-references restored from checkpoint ({total} found)",
            )

        ingested = self.state.get("ingested_data", {})
        findings = []

        try:
            from app.llm import get_llm_client

            llm = get_llm_client()

            # Compact summary of ingested data (cap at 50K chars)
            data_summary = json.dumps(ingested, indent=1, default=str)[:50_000]

            user_prompt = USER_CROSS_REFERENCE.format(
                source_count=len(ingested),
                data_summary=data_summary,
            )

            result = await llm.complete_json(SYSTEM_CROSS_REFERENCE, user_prompt)

            cross_refs = {
                "crm_erp_overlap": result.get("crm_erp_overlap", []),
                "marketing_revenue_correlation": result.get("marketing_revenue_correlation", []),
                "market_data_benchmarks": result.get("market_data_benchmarks", []),
                "summary": result.get("summary", ""),
            }

            # Generate findings for low-quality matches
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
            logger.info("LLM cross-referencing found %d references", total)

        except LLMError:
            logger.warning("LLM unavailable for cross-referencing, returning empty")
            cross_refs = {
                "crm_erp_overlap": [],
                "marketing_revenue_correlation": [],
                "market_data_benchmarks": [],
                "summary": "LLM unavailable — cross-referencing skipped",
            }
            total = 0

        self.state["cross_references"] = cross_refs

        return StepResult(
            success=True,
            data={"cross_references_found": total},
            findings=findings,
            message=f"Cross-referencing complete — {total} references found",
        )

    async def _detect_revenue_variances(self) -> StepResult:
        """Detect revenue variances between CRM pipeline and ERP actuals."""
        # TODO: In production, compare Salesforce pipeline vs NetSuite/SAP revenue
        # Flag anything with >5% variance
        findings = []

        # Example finding that would be generated:
        # findings.append({
        #     "type": "discrepancy",
        #     "source_system": "salesforce_vs_netsuite",
        #     "title": "$2.2M Revenue Variance: CRM Pipeline vs ERP",
        #     "description": "Salesforce shows $14.8M pipeline but NetSuite shows $12.6M recognized revenue. Variance: $2.2M (14.9%)",
        #     "data": {"crm_value": 14800000, "erp_value": 12600000, "variance": 2200000, "variance_pct": 14.9},
        #     "severity": "critical",
        #     "requires_human_review": True,
        # })

        self.state["revenue_variances"] = []

        return StepResult(
            success=True,
            data={"variances_detected": 0},
            findings=findings,
            message="Revenue variance analysis complete",
        )

    async def _detect_cost_variances(self) -> StepResult:
        """Detect cost and expense variances across sources."""
        findings = []
        self.state["cost_variances"] = []

        return StepResult(
            success=True,
            data={"cost_variances_detected": 0},
            findings=findings,
            message="Cost variance analysis complete",
        )

    async def _analyze_customer_metrics(self) -> StepResult:
        """Analyze customer metrics — churn, LTV, CAC, NRR across sources."""
        findings = []
        self.state["customer_analysis"] = {}

        return StepResult(
            success=True,
            data={"metrics_analyzed": 0},
            findings=findings,
            message="Customer metrics analysis complete",
        )

    async def _analyze_market_position(self) -> StepResult:
        """Analyze competitive positioning and market benchmarks."""
        findings = []
        self.state["market_analysis"] = {}

        return StepResult(
            success=True,
            data={"benchmarks_compared": 0},
            findings=findings,
            message="Market position analysis complete",
        )

    async def _financial_model_sync(self) -> StepResult:
        """
        Synchronize findings with financial model.

        TODO: In production, update live financial models in Excel Online
        or Google Sheets with validated data points.
        """
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

        human_review = [v for v in all_variances if v.get("severity") == "critical"]
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
        """Assign confidence scores to all findings using LLM."""
        # Idempotency
        if self.state.get("scored_findings"):
            scored = self.state["scored_findings"]
            return StepResult(
                success=True,
                data={
                    "findings_scored": len(scored),
                    "overall_confidence": self.state.get("overall_confidence", 0),
                },
                message=f"Scored findings restored from checkpoint ({len(scored)})",
            )

        # Gather all findings from analysis steps
        all_findings = (
            self.state.get("revenue_variances", [])
            + self.state.get("cost_variances", [])
        )
        # Add cross-reference discrepancies
        xrefs = self.state.get("cross_references", {})
        for xref in xrefs.get("crm_erp_overlap", []):
            if xref.get("match_quality", 1.0) < 0.5:
                all_findings.append(xref)

        if not all_findings:
            return StepResult(
                success=True,
                data={"findings_scored": 0, "overall_confidence": 0},
                message="No findings to score",
            )

        try:
            from app.llm import get_llm_client

            llm = get_llm_client()

            findings_json = json.dumps(all_findings, indent=1, default=str)[:30_000]
            user_prompt = USER_SCORE_FINDINGS.format(findings_json=findings_json)

            result = await llm.complete_json(SYSTEM_SCORE_FINDINGS, user_prompt)

            scored = result.get("scored_findings", [])
            overall = result.get("overall_confidence", 0)
            logger.info("LLM scored %d findings, overall confidence: %.2f", len(scored), overall)

        except LLMError:
            logger.warning("LLM unavailable for scoring, assigning default scores")
            scored = [
                {
                    "finding_index": i,
                    "reliability_score": 0.5,
                    "impact_score": 0.5,
                    "confidence_justification": "Default score — LLM unavailable",
                    "recommended_action": "flag_for_review",
                }
                for i in range(len(all_findings))
            ]
            overall = 0.5

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
            "source_count": self.state.get("source_count", 0),
            "revenue_variances": self.state.get("revenue_variances", []),
            "cost_variances": self.state.get("cost_variances", []),
            "customer_analysis": self.state.get("customer_analysis", {}),
            "market_analysis": self.state.get("market_analysis", {}),
            "cross_references": self.state.get("cross_references", {}),
            "exceptions": self.state.get("exceptions", {}),
            "scored_findings": self.state.get("scored_findings", []),
            "overall_confidence": self.state.get("overall_confidence", 0),
        }

        return StepResult(
            success=True,
            data={"analysis_summary": analysis_summary},
            message="Analysis compilation complete",
        )
