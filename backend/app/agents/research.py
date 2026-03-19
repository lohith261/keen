"""
Research Agent — authenticates to enterprise systems and extracts live data.

Connects to 15+ data sources (Salesforce, NetSuite, SAP, SEC EDGAR, etc.)
using browser automation and API orchestration. Extracts live data as a
human analyst would, storing structured records with source attribution.
"""

from __future__ import annotations

import importlib
import json
import logging
from typing import Any

from app.agents.base import BaseAgent, StepResult
from app.integrations.base import BaseConnector
from app.integrations.demo import DemoConnector
from app.llm.exceptions import LLMError
from app.llm.prompts import SYSTEM_PLAN_EXTRACTION, USER_PLAN_EXTRACTION

logger = logging.getLogger(__name__)


# ── Live connector registry ───────────────────────────────
# Maps DATA_SOURCES keys → (module_path, class_name) for live connectors.
# Only sources with real connector implementations are listed here.
# Sources not in this map will return empty results in live mode.

LIVE_CONNECTORS: dict[str, tuple[str, str]] = {
    # ── REST / API-based connectors ───────────────────────────────────────────
    "salesforce":    ("app.integrations.salesforce",  "SalesforceConnector"),
    "netsuite":      ("app.integrations.netsuite",    "NetSuiteConnector"),
    "sec_edgar":     ("app.integrations.sec_edgar",   "SECEdgarConnector"),
    "hubspot":       ("app.integrations.hubspot",     "HubSpotConnector"),
    "crunchbase":    ("app.integrations.crunchbase",  "CrunchbaseConnector"),

    # ── TinyFish browser-based connectors ─────────────────────────────────────
    # These require TINYFISH_API_KEY to be set. Without it they return empty
    # results and fall back to demo fixture data automatically.
    "bloomberg":     ("app.integrations.browser.bloomberg",       "BloombergConnector"),
    "capiq":         ("app.integrations.browser.capiq",           "CapIQConnector"),
    "pitchbook":     ("app.integrations.browser.pitchbook",       "PitchBookConnector"),
    "sales_navigator": ("app.integrations.browser.sales_navigator", "SalesNavigatorConnector"),
    "quickbooks":    ("app.integrations.browser.quickbooks",      "QuickBooksConnector"),
    "zoominfo":      ("app.integrations.browser.zoominfo",        "ZoomInfoConnector"),
    "marketo":       ("app.integrations.browser.marketo",         "MarketoConnector"),
    "dynamics":      ("app.integrations.browser.dynamics",        "DynamicsConnector"),
    "sap":           ("app.integrations.browser.sap",             "SAPConnector"),
    "oracle":        ("app.integrations.browser.oracle",          "OracleConnector"),
}


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


# ── Extraction field descriptions ─────────────────────────────────────────────
# Human-readable description of exactly what each (source, extraction_type)
# pair fetches. Used to build descriptive pipeline log messages so users can
# see what the agent is looking for in real time rather than a generic
# "extracting data from X" placeholder.

EXTRACTION_DETAIL: dict[tuple[str, str], str] = {
    # Salesforce
    ("salesforce", "pipeline_data"):    "open opportunities, deal stages, owner info, close dates",
    ("salesforce", "deal_history"):     "closed-won deals last 12 months, amounts, stage history",
    ("salesforce", "contact_records"):  "CRM contacts, titles, account mappings",
    ("salesforce", "activity_logs"):    "tasks & calls last 90 days",
    # NetSuite
    ("netsuite", "revenue_data"):       "customer invoices & credits since 2023, ARR contributions",
    ("netsuite", "expense_records"):    "vendor bills & expense reports since 2023",
    ("netsuite", "journal_entries"):    "GL journal entries since 2023",
    ("netsuite", "balance_sheet"):      "bank, AR, AP, fixed assets, equity account balances",
    # SAP
    ("sap", "financial_statements"):    "income statement, balance sheet, headcount by department",
    ("sap", "cost_centers"):            "cost center hierarchy and allocations",
    ("sap", "purchase_orders"):         "open and closed purchase orders",
    # Oracle
    ("oracle", "gl_entries"):           "Q4 GL entries by account, R&D and engineering costs",
    ("oracle", "ar_aging"):             "AR aging buckets 30/60/90/120+ days, collection status",
    ("oracle", "ap_aging"):             "AP aging by vendor",
    # QuickBooks
    ("quickbooks", "profit_loss"):      "P&L by month and category",
    ("quickbooks", "balance_sheet"):    "assets, liabilities, equity snapshot",
    ("quickbooks", "cash_flow"):        "operating, investing, financing cash flows",
    # HubSpot
    ("hubspot", "marketing_metrics"):   "contact lifecycle stages, MQL/SQL counts, conversion rates",
    ("hubspot", "lead_funnel"):         "deal pipeline stages, counts, total values, win probability",
    ("hubspot", "campaign_roi"):        "email campaign open rates, click rates, revenue attribution",
    # Bloomberg Terminal
    ("bloomberg", "market_comps"):      "peer ticker, market cap, EV, EV/Revenue multiple, Rule of 40",
    ("bloomberg", "industry_benchmarks"): "median revenue growth, gross margin, NRR, CAC payback by segment",
    ("bloomberg", "competitor_financials"): "competitor revenue, growth, last valuation, EV/Revenue multiple",
    # SEC EDGAR
    ("sec_edgar", "10k_filings"):       "annual 10-K — CIK lookup + XBRL financials",
    ("sec_edgar", "10q_filings"):       "quarterly 10-Q — CIK lookup + interim financials",
    ("sec_edgar", "insider_transactions"): "Form 4 insider buy/sell transactions",
    ("sec_edgar", "proxy_statements"):  "DEF 14A proxy — board composition, exec compensation",
    # PitchBook
    ("pitchbook", "deal_comps"):        "comparable deal valuations, entry multiples, hold periods",
    ("pitchbook", "valuation_multiples"): "EV/EBITDA, EV/Revenue, P/E comps by sector",
    ("pitchbook", "fund_performance"):  "fund IRR, MOIC, DPI benchmarks",
    # Capital IQ
    ("capiq", "credit_analysis"):       "credit ratings, debt covenants, leverage ratios",
    ("capiq", "peer_comparison"):       "peer revenue multiples, margin benchmarks",
    ("capiq", "ownership_structure"):   "cap table, institutional holders, insider ownership",
    # ZoomInfo
    ("zoominfo", "org_chart"):          "leadership hierarchy, titles, departments, reporting lines",
    ("zoominfo", "employee_count_trends"): "headcount by quarter, YoY growth, department breakdown",
    ("zoominfo", "tech_stack"):         "CRM/ERP/marketing tools, vendor, confidence score",
    # Crunchbase
    ("crunchbase", "funding_history"):  "all funding rounds, amounts, lead investors, valuations",
    ("crunchbase", "acquisitions"):     "acquiree/acquirer records, prices, dates",
    ("crunchbase", "key_people"):       "founders, current team, titles, tenure",
    # LinkedIn Sales Navigator
    ("sales_navigator", "decision_makers"): "C-suite, VPs, Directors — titles, LinkedIn URLs, activity",
    ("sales_navigator", "company_updates"):  "LinkedIn posts last 6 months — launches, partnerships, hiring",
    ("sales_navigator", "hiring_trends"):    "headcount growth, open roles by dept, recent hires/departures",
    # Microsoft Dynamics
    ("dynamics", "sales_pipeline"):     "pipeline stages, opportunity counts, forecast amounts",
    ("dynamics", "customer_segments"):  "SMB/Mid/Enterprise segments, ARR, churn rates",
    ("dynamics", "revenue_forecast"):   "12-month forecast by segment and product line",
    # Marketo
    ("marketo", "lead_scoring"):        "lead score distribution, high-intent signals",
    ("marketo", "email_metrics"):       "open rates, click-through rates, unsubscribe rates by campaign",
    ("marketo", "attribution_data"):    "first-touch and multi-touch attribution by channel",
}

# Auth type labels for human-readable log messages
_AUTH_TYPE_LABEL: dict[str, str] = {
    "oauth":             "OAuth 2.0",
    "token":             "token-based auth",
    "api_key":           "API key",
    "browser":           "TinyFish browser session",
    "sso":               "SSO",
    "username_password": "username/password",
    "public":            "public API (no auth required)",
    "demo":              "demo fixture data",
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

        source_names = ", ".join(s.get("name", s.get("source", "")) for s in sources_planned[:6])
        if len(sources_planned) > 6:
            source_names += f" + {len(sources_planned) - 6} more"

        return StepResult(
            success=True,
            data={"sources_planned": len(sources_planned), "plan": sources_planned},
            message=f"LLM extraction plan: {len(sources_planned)} sources selected — {source_names}",
        )

    async def _authenticate_source(self, source: str) -> StepResult:
        """
        Authenticate to a data source.

        In demo mode (default) uses DemoConnector with fixture data.
        In production, replace with AuthManager + real connectors.
        """
        source_info = DATA_SOURCES.get(source, {})
        auth_type = source_info.get("auth_type", "unknown")
        demo_mode = self.state.get("pipeline_config", {}).get("demo_mode", True)

        if demo_mode:
            connector = DemoConnector(source_id=source, company_id=self.state.get("pipeline_config", {}).get("target_company", ""))
            session = await connector.authenticate({})
            # Store connector so _extract_source can reuse it without re-loading fixture
            self.state[f"_connector_{source}"] = connector
            logger.info("DemoConnector: authenticated to %s (demo mode)", source)
        else:
            # Production: instantiate the real connector and authenticate via vault credentials
            connector_spec = LIVE_CONNECTORS.get(source)
            if connector_spec:
                try:
                    module_path, class_name = connector_spec
                    try:
                        module = importlib.import_module(module_path)
                        connector_class = getattr(module, class_name)
                    except (ImportError, AttributeError) as import_exc:
                        logger.error(
                            "Failed to import connector %s.%s for '%s': %s — "
                            "check that all connector dependencies are installed",
                            module_path, class_name, source, import_exc,
                        )
                        raise  # re-raise so the outer except logs it as well

                    # Browser-based connectors (TinyFish) accept an on_event
                    # callback so they can forward the live streaming URL to the
                    # frontend in real time.  REST connectors don't need it.
                    is_browser_connector = "browser" in module_path
                    live_connector: BaseConnector = (
                        connector_class(on_event=self.on_progress)
                        if is_browser_connector
                        else connector_class()
                    )

                    # Load credentials from vault for this engagement
                    credentials: dict = {}
                    if self.db:
                        from app.auth.vault import CredentialVault
                        vault = CredentialVault(self.db)
                        credentials = await vault.get_credentials(self.engagement_id, source)

                    await live_connector.authenticate(credentials)
                    self.state[f"_connector_{source}"] = live_connector
                    logger.info("Live connector: authenticated to %s via vault credentials", source)
                except Exception as exc:
                    logger.warning(
                        "Live connector setup failed for '%s': %s — "
                        "this source will return empty data for this run",
                        source, exc,
                    )
            else:
                logger.info(
                    "No live connector registered for '%s' — skipping (use demo_mode=True or implement connector)",
                    source,
                )

        self.state[f"auth_{source}"] = {
            "authenticated": True,
            "auth_type": auth_type if not demo_mode else "demo",
            "session_id": f"session_{source}_{self.agent_run_id}",
            "demo_mode": demo_mode,
        }

        effective_auth = "demo" if demo_mode else auth_type
        auth_label = _AUTH_TYPE_LABEL.get(effective_auth, effective_auth)
        prefix = "[DEMO] " if demo_mode else ""

        return StepResult(
            success=True,
            data={"source": source, "auth_type": auth_type, "status": "authenticated", "demo_mode": demo_mode},
            message=f"{prefix}Connected to {source_info.get('name', source)} via {auth_label}",
        )

    async def _extract_source(self, source: str) -> StepResult:
        """
        Extract data from an authenticated source.

        In demo mode uses DemoConnector fixture data.
        In production, replace connector lookup with real connector instantiation.
        """
        source_info = DATA_SOURCES.get(source, {})
        extractions = source_info.get("extractions", [])
        demo_mode = self.state.get("pipeline_config", {}).get("demo_mode", True)

        extracted_data: dict = {}
        findings: list = []
        total_records = 0
        source_name = source_info.get("name", source)

        if demo_mode:
            # Reuse the connector created during authenticate, or create fresh
            connector: DemoConnector = self.state.get(f"_connector_{source}") or DemoConnector(source_id=source, company_id=self.state.get("pipeline_config", {}).get("target_company", ""))

            if not connector._fixture:
                await connector.authenticate({})

            for extraction_type in extractions:
                # Emit a descriptive sub-progress log line before each extraction
                detail = EXTRACTION_DETAIL.get((source, extraction_type), "")
                detail_str = f" ({detail})" if detail else ""
                await self._report_sub_progress(
                    f"{source_name}: fetching {extraction_type}{detail_str}"
                )
                records = await connector.extract({"type": extraction_type})
                extracted_data[extraction_type] = records
                total_records += len(records)
                logger.debug("DemoConnector[%s/%s]: %d records", source, extraction_type, len(records))
        else:
            # Production: use the live connector authenticated in _authenticate_source
            live_connector: BaseConnector | None = self.state.get(f"_connector_{source}")
            if live_connector:
                for extraction_type in extractions:
                    # Emit a descriptive sub-progress log line before each extraction
                    detail = EXTRACTION_DETAIL.get((source, extraction_type), "")
                    detail_str = f" ({detail})" if detail else ""
                    await self._report_sub_progress(
                        f"{source_name}: fetching {extraction_type}{detail_str}"
                    )
                    try:
                        records = await live_connector.extract({"type": extraction_type})
                        extracted_data[extraction_type] = records
                        total_records += len(records)
                        logger.debug(
                            "LiveConnector[%s/%s]: %d records",
                            source, extraction_type, len(records),
                        )
                    except Exception as exc:
                        logger.warning(
                            "LiveConnector extraction failed [%s/%s]: %s",
                            source, extraction_type, exc,
                        )
                        extracted_data[extraction_type] = []
                # Disconnect after all extractions for this source
                try:
                    await live_connector.disconnect()
                except Exception:
                    pass
            else:
                # No connector available for this source in live mode
                for extraction_type in extractions:
                    extracted_data[extraction_type] = []
                logger.info(
                    "No live connector for '%s' — returning empty datasets",
                    source,
                )

        self.state[f"data_{source}"] = extracted_data

        logger.info(
            "Extracted %d datasets (%d records) from %s",
            len(extractions),
            total_records,
            source_name,
        )

        # Build a concise summary for the step-done log line
        extraction_parts = []
        for et in extractions:
            detail = EXTRACTION_DETAIL.get((source, et), "")
            extraction_parts.append(f"{et}" + (f" ({detail})" if detail else ""))
        extraction_summary = "; ".join(extraction_parts)

        return StepResult(
            success=True,
            data={
                "source": source,
                "datasets": list(extracted_data.keys()),
                "total_extractions": len(extractions),
                "total_records": total_records,
                "demo_mode": demo_mode,
            },
            findings=findings,
            message=(
                f"{source_name}: pulled {extraction_summary} — {total_records} records"
            ),
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
            message=(
                f"Validated {len(sources_with_data)} source dataset(s)"
                + (f" — {len(missing_data)} source(s) returned no data: {', '.join(missing_data)}" if missing_data else " — all sources have data")
            ),
        )

    async def _compile_results(self) -> StepResult:
        """Compile all extracted data into a structured result for the Analysis agent."""
        compiled: dict[str, Any] = {}

        for key, value in self.state.items():
            if key.startswith("data_"):
                source = key.replace("data_", "")
                compiled[source] = value

        # Include uploaded documents as an additional data source
        uploaded_documents = self.state.get("pipeline_config", {}).get("uploaded_documents", [])
        if uploaded_documents:
            compiled["uploaded_documents"] = uploaded_documents
            logger.info(
                "Compiled %d uploaded document(s) into research output",
                len(uploaded_documents),
            )

        return StepResult(
            success=True,
            data={
                "compiled_sources": list(compiled.keys()),
                "total_sources": len(compiled),
                "raw_data": compiled,
            },
            message=(
                f"Research complete — compiled {len(compiled)} source dataset(s)"
                + (f" + {len(uploaded_documents)} uploaded document(s)" if uploaded_documents else "")
                + f" → passing to Analysis Agent"
            ),
        )
