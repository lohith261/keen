"""
Bloomberg Terminal connector.

Extracts market comparables, industry benchmarks, and competitor financials
from Bloomberg via TinyFish AI browser automation.

Authentication: Bloomberg Anywhere (web) — username + password.
Required credentials keys:
  - username     Bloomberg login email / username
  - password     Bloomberg login password
  - company_name Target company to search (used in queries)

Bloomberg URL: https://bba.bloomberg.net  (Bloomberg Anywhere web)
"""

from __future__ import annotations

import logging
from typing import Any

from app.integrations.browser.base import BaseBrowserConnector
from app.integrations.browser.tinyfish import TinyFishSession

logger = logging.getLogger(__name__)


class BloombergConnector(BaseBrowserConnector):
    """Connector for Bloomberg Terminal data via TinyFish browser automation."""

    system_name = "bloomberg"
    category = "market_data"
    login_url = "https://bba.bloomberg.net"

    # ── Login flow ────────────────────────────────────────────────────────────

    async def _login(self, session: TinyFishSession, credentials: dict) -> None:
        """
        Authenticate to Bloomberg Anywhere web portal.

        Flow: Enter username → Continue → Enter password → Sign In
        Bloomberg may show a two-step login form (username first, then password).
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        if not username or not password:
            logger.warning("Bloomberg: credentials missing username or password")
            return

        # Step 1: Enter username
        await session.act(
            "Find the username or email input field and type the username",
            context={"username": username},
        )

        # Step 2: Click Continue / Next if shown
        await session.act(
            "If there is a 'Continue' or 'Next' button, click it and wait for the next step"
        )

        # Step 3: Enter password
        await session.act(
            "Find the password input field and type the password",
            context={"password": password},
        )

        # Step 4: Submit
        await session.act(
            "Click the 'Sign In', 'Log In', or 'Submit' button and wait for the dashboard to load"
        )

        logger.info("Bloomberg: login flow completed")

    # ── Extraction ────────────────────────────────────────────────────────────

    async def _do_extract(
        self,
        session: TinyFishSession,
        query_type: str,
        company_name: str,
    ) -> list[dict]:
        """Route to the correct Bloomberg extraction based on query_type."""
        extractors = {
            "market_comps": self._extract_market_comps,
            "industry_benchmarks": self._extract_industry_benchmarks,
            "competitor_financials": self._extract_competitor_financials,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("Bloomberg: unknown query type '%s'", query_type)
            return []

        return await extractor(session, company_name)

    async def _extract_market_comps(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract public market comparables for the target company's sector."""
        # Navigate to the equity screening / comps page
        await session.navigate("https://bba.bloomberg.net/markets/equities")

        await session.act(
            f"Search for '{company_name}' and navigate to its company profile page"
        )
        await session.act(
            "Find the 'Peer Analysis' or 'Comparable Companies' section"
        )

        records = await session.extract(
            instruction=(
                "Extract a list of comparable public companies from the peer analysis section. "
                "For each company include: ticker, company name, market cap (in millions), "
                "enterprise value (in millions), TTM revenue (in millions), EV/Revenue multiple, "
                "revenue growth percentage, gross margin percentage, and Rule of 40 score."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "ticker": {"type": "string"},
                        "name": {"type": "string"},
                        "market_cap_m": {"type": "number"},
                        "ev_m": {"type": "number"},
                        "revenue_ttm_m": {"type": "number"},
                        "ev_revenue": {"type": "number"},
                        "revenue_growth_pct": {"type": "number"},
                        "gross_margin_pct": {"type": "number"},
                        "rule_of_40": {"type": "number"},
                    },
                },
            },
        )
        return records if isinstance(records, list) else [records]

    async def _extract_industry_benchmarks(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract industry benchmark statistics for the target company's sector."""
        await session.navigate("https://bba.bloomberg.net/markets/equities/sectors")

        await session.act(
            f"Navigate to the industry or sector benchmarks for the same segment as '{company_name}'. "
            "Look for B2B SaaS, enterprise software, or cloud software benchmarks."
        )

        benchmarks = await session.extract(
            instruction=(
                "Extract the industry benchmark statistics including: segment name, "
                "median revenue growth, median gross margin, median EV/Revenue multiple, "
                "median net revenue retention, median CAC payback months, "
                "median magic number, median Rule of 40, top quartile EV/Revenue, "
                "bottom quartile EV/Revenue, and peer count."
            ),
            schema={
                "type": "object",
                "properties": {
                    "segment": {"type": "string"},
                    "median_revenue_growth_pct": {"type": "number"},
                    "median_gross_margin_pct": {"type": "number"},
                    "median_ev_revenue_multiple": {"type": "number"},
                    "median_net_revenue_retention_pct": {"type": "number"},
                    "median_cac_payback_months": {"type": "number"},
                    "median_magic_number": {"type": "number"},
                    "median_rule_of_40": {"type": "number"},
                    "top_quartile_ev_revenue": {"type": "number"},
                    "bottom_quartile_ev_revenue": {"type": "number"},
                    "peer_count": {"type": "integer"},
                },
            },
        )
        return [benchmarks] if isinstance(benchmarks, dict) else benchmarks

    async def _extract_competitor_financials(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract private competitor financial estimates."""
        await session.act(
            f"Navigate to the competitive landscape or comparable private companies section "
            f"for '{company_name}'. Look for private company financials or deal comparables."
        )

        records = await session.extract(
            instruction=(
                "Extract a list of private competitors with their estimated financials. "
                "Include: company name, stage (Private/Public/Acquired), estimated revenue in millions, "
                "estimated growth percentage, last valuation in millions, implied EV/Revenue, "
                "and key differentiator."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "company": {"type": "string"},
                        "stage": {"type": "string"},
                        "est_revenue_m": {"type": "number"},
                        "est_growth_pct": {"type": "number"},
                        "last_valuation_m": {"type": "number"},
                        "ev_revenue_implied": {"type": "number"},
                        "differentiator": {"type": "string"},
                    },
                },
            },
        )
        return records if isinstance(records, list) else [records]
