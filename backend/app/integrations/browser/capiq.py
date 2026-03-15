"""
S&P Capital IQ (CapIQ) connector.

Extracts credit analysis, peer comparison, and ownership/cap table data
from Capital IQ via TinyFish AI browser automation.

Authentication: S&P Global Capital IQ platform — username + password.
Required credentials keys:
  - username     Capital IQ login email
  - password     Capital IQ login password
  - company_name Target company to research

CapIQ URL: https://www.capitaliq.spglobal.com
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector
from app.integrations.browser.tinyfish import TinyFishSession

logger = logging.getLogger(__name__)


class CapIQConnector(BaseBrowserConnector):
    """Connector for S&P Capital IQ data via TinyFish browser automation."""

    system_name = "capiq"
    category = "market_data"
    login_url = "https://www.capitaliq.spglobal.com/web/client#auth/login"

    # ── Login flow ────────────────────────────────────────────────────────────

    async def _login(self, session: TinyFishSession, credentials: dict) -> None:
        """Authenticate to Capital IQ platform."""
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        if not username or not password:
            logger.warning("CapIQ: credentials missing username or password")
            return

        await session.act(
            "Find the email or username field and enter the username",
            context={"username": username},
        )
        await session.act(
            "Find the password field and enter the password",
            context={"password": password},
        )
        await session.act(
            "Click the 'Sign In' or 'Log In' button and wait for the main dashboard to appear"
        )

        logger.info("CapIQ: login flow completed")

    # ── Extraction ────────────────────────────────────────────────────────────

    async def _do_extract(
        self,
        session: TinyFishSession,
        query_type: str,
        company_name: str,
    ) -> list[dict]:
        extractors = {
            "credit_analysis": self._extract_credit_analysis,
            "peer_comparison": self._extract_peer_comparison,
            "ownership_structure": self._extract_ownership_structure,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("CapIQ: unknown query type '%s'", query_type)
            return []
        return await extractor(session, company_name)

    async def _search_company(self, session: TinyFishSession, company_name: str) -> None:
        """Navigate to the target company's profile page."""
        await session.act(
            f"Use the search bar to search for '{company_name}' and click on the correct company result"
        )
        await session.act(
            "Wait for the company profile page to fully load"
        )

    async def _extract_credit_analysis(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract liquidity, leverage, and credit metrics."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Financials' or 'Credit Analysis' section of the company profile"
        )

        credit = await session.extract(
            instruction=(
                "Extract the credit and liquidity analysis data including: "
                "cash and equivalents, short-term investments, undrawn credit facility/revolver, "
                "total liquidity, average monthly cash burn, runway in months, "
                "current ratio, quick ratio, total debt, net debt, debt-to-equity ratio, "
                "net leverage description, interest coverage, implied credit score, "
                "and any key financial covenants."
            ),
            schema={
                "type": "object",
                "properties": {
                    "as_of": {"type": "string"},
                    "liquidity": {
                        "type": "object",
                        "properties": {
                            "cash_and_equivalents": {"type": "number"},
                            "short_term_investments": {"type": "number"},
                            "undrawn_revolver": {"type": "number"},
                            "total_liquidity": {"type": "number"},
                            "monthly_cash_burn_avg": {"type": "number"},
                            "runway_months": {"type": "number"},
                            "current_ratio": {"type": "number"},
                            "quick_ratio": {"type": "number"},
                        },
                    },
                    "leverage": {
                        "type": "object",
                        "properties": {
                            "total_debt": {"type": "number"},
                            "net_debt": {"type": "number"},
                            "debt_to_equity": {"type": "number"},
                            "net_leverage": {"type": "string"},
                            "interest_coverage": {"type": "string"},
                        },
                    },
                    "credit_score_implied": {"type": "string"},
                    "key_covenants_if_leveraged": {"type": "array", "items": {"type": "string"}},
                },
            },
        )
        return [credit] if isinstance(credit, dict) else credit

    async def _extract_peer_comparison(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract peer benchmarking metrics vs. comparable companies."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Benchmarking' or 'Peer Comparison' section"
        )

        peers = await session.extract(
            instruction=(
                "Extract the peer comparison table. For each metric row include: "
                "metric name, the target company's value, peer median value, "
                "percentile ranking, and signal/interpretation text."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "metric": {"type": "string"},
                        "acme": {"type": "string"},
                        "peer_median": {"type": "string"},
                        "percentile": {"type": "number"},
                        "signal": {"type": "string"},
                    },
                },
            },
        )
        return peers if isinstance(peers, list) else [peers]

    async def _extract_ownership_structure(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract cap table, shareholder structure, and liquidation preferences."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Ownership' or 'Cap Table' or 'Shareholders' section"
        )

        ownership = await session.extract(
            instruction=(
                "Extract the full ownership structure including: "
                "total shares fully diluted, common shares outstanding, options and warrants, "
                "cap table (for each shareholder: name, shares, percentage basic, percentage diluted, "
                "total investment amount in millions, series), and "
                "liquidation preferences (series, amount, preference type). "
                "Also include total liquidation stack."
            ),
            schema={
                "type": "object",
                "properties": {
                    "total_shares_fully_diluted": {"type": "number"},
                    "common_shares_outstanding": {"type": "number"},
                    "options_and_warrants": {"type": "number"},
                    "cap_table": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "shareholder": {"type": "string"},
                                "shares": {"type": "number"},
                                "pct_basic": {"type": "number"},
                                "pct_diluted": {"type": "number"},
                                "investment_total_m": {"type": "number"},
                                "series": {"type": "string"},
                            },
                        },
                    },
                    "liquidation_preferences": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "series": {"type": "string"},
                                "amount_m": {"type": "number"},
                                "preference": {"type": "string"},
                            },
                        },
                    },
                    "total_liquidation_stack_m": {"type": "number"},
                },
            },
        )
        return [ownership] if isinstance(ownership, dict) else ownership
