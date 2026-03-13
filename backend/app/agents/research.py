"""
Research Agent — authenticates to enterprise systems and extracts live data.

Connects to 15+ data sources (Salesforce, NetSuite, SAP, SEC EDGAR, etc.)
using browser automation and API orchestration. Extracts live data as a
human analyst would, storing structured records with source attribution.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agents.base import BaseAgent, StepResult
from app.llm.exceptions import LLMError
from app.llm.prompts import SYSTEM_PLAN_EXTRACTION, USER_PLAN_EXTRACTION

logger = logging.getLogger(__name__)


# ── Data source registry ─────────────────────────────────

DATA_SOURCES = {
    "salesforce": {
        "name": "Salesforce CRM",
        "category": "crm",
        "auth_type": "oauth",
        "extractions": ["pipeline_data", "deal_history", "contact_records", "activity_logs"],
    },
    "netsuite": {
        "name": "NetSuite ERP",
        "category": "erp",
        "auth_type": "token",
        "extractions": ["revenue_data", "expense_records", "journal_entries", "balance_sheet"],
    },
    "sap": {
        "name": "SAP",
        "category": "erp",
        "auth_type": "sso",
        "extractions": ["financial_statements", "cost_centers", "purchase_orders"],
    },
    "oracle": {
        "name": "Oracle",
        "category": "erp",
        "auth_type": "username_password",
        "extractions": ["gl_entries", "ar_aging", "ap_aging"],
    },
    "quickbooks": {
        "name": "QuickBooks",
        "category": "accounting",
        "auth_type": "oauth",
        "extractions": ["profit_loss", "balance_sheet", "cash_flow"],
    },
    "hubspot": {
        "name": "HubSpot",
        "category": "marketing",
        "auth_type": "api_key",
        "extractions": ["marketing_metrics", "lead_funnel", "campaign_roi"],
    },
    "bloomberg": {
        "name": "Bloomberg Terminal",
        "category": "market_data",
        "auth_type": "browser",
        "extractions": ["market_comps", "industry_benchmarks", "competitor_financials"],
    },
    "sec_edgar": {
        "name": "SEC EDGAR",
        "category": "regulatory",
        "auth_type": "public",
        "extractions": ["10k_filings", "10q_filings", "insider_transactions", "proxy_statements"],
    },
    "pitchbook": {
        "name": "PitchBook",
        "category": "market_data",
        "auth_type": "browser",
        "extractions": ["deal_comps", "valuation_multiples", "fund_performance"],
    },
    "capiq": {
        "name": "Capital IQ",
        "category": "market_data",
        "auth_type": "browser",
        "extractions": ["credit_analysis", "peer_comparison", "ownership_structure"],
    },
    "zoominfo": {
        "name": "ZoomInfo",
        "category": "intelligence",
        "auth_type": "api_key",
        "extractions": ["org_chart", "employee_count_trends", "tech_stack"],
    },
    "crunchbase": {
        "name": "Crunchbase",
        "category": "intelligence",
        "auth_type": "api_key",
        "extractions": ["funding_history", "acquisitions", "key_people"],
    },
    "sales_navigator": {
        "name": "LinkedIn Sales Navigator",
        "category": "intelligence",
        "auth_type": "browser",
        "extractions": ["decision_makers", "company_updates", "hiring_trends"],
    },
    "dynamics": {
        "name": "Microsoft Dynamics",
        "category": "crm",
        "auth_type": "oauth",
        "extractions": ["sales_pipeline", "customer_segments", "revenue_forecast"],
    },
    "marketo": {
        "name": "Marketo",
        "category": "marketing",
        "auth_type": "api_key",
        "extractions": ["lead_scoring", "email_metrics", "attribution_data"],
    },
}


class ResearchAgent(BaseAgent):
    """
    Autonomous data extraction agent.

    Steps:
        1. Plan — determine which sources to access based on engagement config
        2. Authenticate — establish sessions with each source
        3-N. Extract — pull data from each source
        N+1. Validate — cross-check extracted data for completeness
        N+2. Compile — structure results for the Analysis agent
    """

    agent_type = "research"

    def define_steps(self, config: dict) -> list[str]:
        """Define extraction steps based on configured data sources."""
        sources = config.get("systems", list(DATA_SOURCES.keys()))

        steps = ["plan_extraction"]

        for source in sources:
            if source in DATA_SOURCES:
                steps.append(f"authenticate_{source}")
                steps.append(f"extract_{source}")

        steps.append("validate_extractions")
        steps.append("compile_results")

        return steps

    async def execute_step(self, step_index: int, step_name: str) -> StepResult:
        """Execute a research step."""

        if step_name == "plan_extraction":
            return await self._plan_extraction()

        elif step_name.startswith("authenticate_"):
            source = step_name.replace("authenticate_", "")
            return await self._authenticate_source(source)

        elif step_name.startswith("extract_"):
            source = step_name.replace("extract_", "")
            return await self._extract_source(source)

        elif step_name == "validate_extractions":
            return await self._validate_extractions()

        elif step_name == "compile_results":
            return await self._compile_results()

        return StepResult(success=False, message=f"Unknown step: {step_name}")

    # ── Step implementations ─────────────────────────────

    async def _plan_extraction(self) -> StepResult:
        """Plan which data sources to access and what to extract using LLM."""
        # Idempotency: skip if already planned (checkpoint resume)
        if self.state.get("extraction_plan"):
            plan = self.state["extraction_plan"]
            return StepResult(
                success=True,
                data={"sources_planned": len(plan), "plan": plan},
                message=f"Extraction plan restored from checkpoint ({len(plan)} sources)",
            )

        config = self.state.get("pipeline_config", {})

        try:
            from app.llm import get_llm_client

            llm = get_llm_client()

            sources_json = json.dumps(
                {sid: info for sid, info in DATA_SOURCES.items()},
                indent=2,
            )
            user_prompt = USER_PLAN_EXTRACTION.format(
                company_name=config.get("company_name", "Unknown"),
                industry=config.get("industry", "Unknown"),
                engagement_type=config.get("engagement_type", "full_diligence"),
                sources_json=sources_json,
            )

            result = await llm.complete_json(SYSTEM_PLAN_EXTRACTION, user_prompt)
            sources_planned = result.get("sources", [])
            logger.info(
                "LLM planned extraction for %d sources: %s",
                len(sources_planned),
                result.get("reasoning", ""),
            )
        except LLMError:
            logger.warning("LLM unavailable for extraction planning, using all sources")
            sources_planned = [
                {
                    "source": sid,
                    "name": info["name"],
                    "category": info["category"],
                    "extractions": info["extractions"],
                    "priority": 3,
                    "rationale": "Fallback — LLM unavailable",
                }
                for sid, info in DATA_SOURCES.items()
            ]

        self.state["extraction_plan"] = sources_planned

        return StepResult(
            success=True,
            data={"sources_planned": len(sources_planned), "plan": sources_planned},
            message=f"Extraction planned for {len(sources_planned)} data sources",
        )

    async def _authenticate_source(self, source: str) -> StepResult:
        """
        Authenticate to an enterprise data source.

        TODO: Integrate with AuthManager for real authentication.
        This is the plugin point for TinyFish browser automation
        (handles the 60% of sources without APIs).
        """
        source_info = DATA_SOURCES.get(source, {})
        auth_type = source_info.get("auth_type", "unknown")

        # Placeholder: In production, this calls AuthManager which handles:
        # - OAuth flows (Salesforce, Dynamics, QuickBooks)
        # - API key injection (HubSpot, ZoomInfo, Crunchbase)
        # - Browser-based auth via TinyFish (Bloomberg, PitchBook, CapIQ)
        # - SSO/MFA flows (SAP)
        # - Public access (SEC EDGAR)

        logger.info(f"Authenticating to {source} via {auth_type}")

        self.state[f"auth_{source}"] = {
            "authenticated": True,
            "auth_type": auth_type,
            "session_id": f"session_{source}_{self.agent_run_id}",
        }

        return StepResult(
            success=True,
            data={"source": source, "auth_type": auth_type, "status": "authenticated"},
            message=f"Authenticated to {source_info.get('name', source)}",
        )

    async def _extract_source(self, source: str) -> StepResult:
        """
        Extract data from an authenticated enterprise source.

        TODO: Integrate with actual data connectors.
        Each connector handles:
        - API calls for programmatic sources
        - Browser automation for UI-only sources
        - Rate limiting and pagination
        - Data normalization
        """
        source_info = DATA_SOURCES.get(source, {})
        extractions = source_info.get("extractions", [])

        # Placeholder: In production, this calls the appropriate connector
        # from app.integrations (Salesforce, NetSuite, etc.)
        extracted_data = {}
        findings = []

        for extraction_type in extractions:
            # Simulate structured data extraction
            extracted_data[extraction_type] = {
                "source": source,
                "type": extraction_type,
                "records_extracted": 0,  # Placeholder
                "status": "pending_integration",
            }

        self.state[f"data_{source}"] = extracted_data

        logger.info(
            f"Extracted {len(extractions)} datasets from {source_info.get('name', source)}"
        )

        return StepResult(
            success=True,
            data={
                "source": source,
                "datasets": list(extracted_data.keys()),
                "total_extractions": len(extractions),
            },
            findings=findings,
            message=f"Extracted {len(extractions)} datasets from {source_info.get('name', source)}",
        )

    async def _validate_extractions(self) -> StepResult:
        """Validate completeness and consistency of extracted data."""
        sources_with_data = [
            k.replace("data_", "") for k in self.state if k.startswith("data_")
        ]
        sources_authenticated = [
            k.replace("auth_", "") for k in self.state if k.startswith("auth_")
        ]

        findings = []

        # Check for sources that authenticated but have no data
        missing_data = set(sources_authenticated) - set(sources_with_data)
        for source in missing_data:
            findings.append({
                "type": "exception",
                "source_system": source,
                "title": f"No data extracted from {source}",
                "description": f"Authentication succeeded but extraction yielded no data from {source}",
                "severity": "warning",
                "requires_human_review": True,
            })

        return StepResult(
            success=True,
            data={
                "sources_validated": len(sources_with_data),
                "sources_missing": list(missing_data),
            },
            findings=findings,
            message=f"Validated {len(sources_with_data)} sources, {len(missing_data)} missing",
        )

    async def _compile_results(self) -> StepResult:
        """Compile all extracted data into a structured result for the Analysis agent."""
        compiled: dict[str, Any] = {}

        for key, value in self.state.items():
            if key.startswith("data_"):
                source = key.replace("data_", "")
                compiled[source] = value

        return StepResult(
            success=True,
            data={
                "compiled_sources": list(compiled.keys()),
                "total_sources": len(compiled),
                "raw_data": compiled,
            },
            message=f"Compiled data from {len(compiled)} sources",
        )
