"""
PitchBook connector.

Extracts M&A deal comparables, valuation multiples, and fund performance data
from PitchBook via TinyFish AI browser automation.

Authentication: PitchBook — username + password (email login).
Required credentials keys:
  - username     PitchBook account email
  - password     PitchBook account password
  - company_name Target company to research

PitchBook URL: https://pitchbook.com
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector
from app.integrations.browser.tinyfish import TinyFishSession

logger = logging.getLogger(__name__)


class PitchBookConnector(BaseBrowserConnector):
    """Connector for PitchBook data via TinyFish browser automation."""

    system_name = "pitchbook"
    category = "market_data"
    login_url = "https://pitchbook.com/login"

    # ── Login flow ────────────────────────────────────────────────────────────

    async def _login(self, session: TinyFishSession, credentials: dict) -> None:
        """Authenticate to PitchBook platform."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        if not username or not password:
            logger.warning("PitchBook: credentials missing username or password")
            return

        await session.act(
            "Find the email input field and type the username/email",
            context={"username": username},
        )
        await session.act(
            "Find the password field and type the password",
            context={"password": password},
        )
        await session.act(
            "Click the 'Sign In' or 'Log In' button and wait until the PitchBook dashboard loads"
        )

        logger.info("PitchBook: login flow completed")

    # ── Extraction ────────────────────────────────────────────────────────────

    async def _do_extract(
        self,
        session: TinyFishSession,
        query_type: str,
        company_name: str,
    ) -> list[dict]:
        extractors = {
            "deal_comps": self._extract_deal_comps,
            "valuation_multiples": self._extract_valuation_multiples,
            "fund_performance": self._extract_fund_performance,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("PitchBook: unknown query type '%s'", query_type)
            return []
        return await extractor(session, company_name)

    async def _search_company(self, session: TinyFishSession, company_name: str) -> None:
        """Navigate to the target company's PitchBook profile."""
        await session.act(
            f"Use the search bar at the top to search for '{company_name}' and click on "
            "the correct company in the results list"
        )
        await session.act("Wait for the company profile to fully load")

    async def _extract_deal_comps(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract recent M&A deal comparables in the target company's segment."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Deals' or 'Comparable Transactions' section. "
            "Filter for M&A deals in the same sector from the past 3 years."
        )

        deals = await session.extract(
            instruction=(
                "Extract the list of comparable M&A transactions. For each deal include: "
                "target company name, acquirer name, deal date (YYYY-MM-DD), "
                "deal value in millions, revenue at time of deal in millions, "
                "EV/Revenue multiple, ARR at deal in millions, revenue growth percentage, "
                "and deal type (e.g. Buyout, Strategic Acquisition, Platform Roll-up)."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "target": {"type": "string"},
                        "acquirer": {"type": "string"},
                        "deal_date": {"type": "string"},
                        "deal_value_m": {"type": "number"},
                        "revenue_at_deal_m": {"type": "number"},
                        "ev_revenue": {"type": "number"},
                        "arr_at_deal_m": {"type": "number"},
                        "growth_pct": {"type": "number"},
                        "deal_type": {"type": "string"},
                    },
                },
            },
            paginate=True,
        )
        return deals if isinstance(deals, list) else [deals]

    async def _extract_valuation_multiples(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract PE/M&A valuation multiple benchmarks for the company's segment."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Valuation' or 'Multiples' section of the company profile. "
            "Look for benchmark valuation data for the company's sector and ARR range."
        )

        multiples = await session.extract(
            instruction=(
                "Extract the valuation multiples benchmarking data including: "
                "segment description, sample size, ARR range, median EV/ARR, mean EV/ARR, "
                "25th percentile EV/ARR, 75th percentile EV/ARR, top decile EV/ARR, "
                "growth premium per 10% additional growth, gross margin premium per 5% improvement, "
                "NRR premium above 120%, and implied valuation range for the target company "
                "(low, mid, high, and basis description)."
            ),
            schema={
                "type": "object",
                "properties": {
                    "segment": {"type": "string"},
                    "sample_size": {"type": "integer"},
                    "arr_range": {"type": "string"},
                    "ev_arr_median": {"type": "number"},
                    "ev_arr_mean": {"type": "number"},
                    "ev_arr_25th_percentile": {"type": "number"},
                    "ev_arr_75th_percentile": {"type": "number"},
                    "ev_arr_top_decile": {"type": "number"},
                    "growth_premium_per_10pct": {"type": "number"},
                    "gross_margin_premium_per_5pct": {"type": "number"},
                    "nrr_premium_above_120pct": {"type": "number"},
                    "implied_range_for_target": {
                        "type": "object",
                        "properties": {
                            "low": {"type": "number"},
                            "mid": {"type": "number"},
                            "high": {"type": "number"},
                            "basis": {"type": "string"},
                        },
                    },
                },
            },
        )
        return [multiples] if isinstance(multiples, dict) else multiples

    async def _extract_fund_performance(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract investor fund performance data for the target company's backers."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Investors' section of the company profile to see VC/PE backers"
        )
        await session.act(
            "Click on each lead investor to view their fund performance metrics"
        )

        funds = await session.extract(
            instruction=(
                "Extract the fund performance data for each investor. Include: "
                "fund name, vintage year, IRR percentage, MOIC (multiple on invested capital), "
                "DPI (distributions to paid-in), fund size in millions, and notable exits list."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "fund": {"type": "string"},
                        "vintage": {"type": "integer"},
                        "irr_pct": {"type": "number"},
                        "moic": {"type": "number"},
                        "dpi": {"type": "number"},
                        "fund_size_m": {"type": "number"},
                        "notable_exits": {"type": "array", "items": {"type": "string"}},
                    },
                },
            },
        )
        return funds if isinstance(funds, list) else [funds]
