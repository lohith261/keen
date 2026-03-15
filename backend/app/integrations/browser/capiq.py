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

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class CapIQConnector(BaseBrowserConnector):
    """Connector for S&P Capital IQ data via TinyFish browser automation."""

    system_name = "capiq"
    category = "market_data"
    login_url = "https://www.capitaliq.spglobal.com/web/client#auth/login"

    # ── Goal builder ──────────────────────────────────────────────────────────

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://www.capitaliq.spglobal.com/web/client#auth/login. "
            f"Find the email or username field and enter '{username}'. "
            f"Find the password field and enter '{password}'. "
            f"Click the 'Sign In' or 'Log In' button and wait for the main dashboard. "
            f"Use the search bar to search for '{company_name}' and click the correct "
            f"company result to open its profile page. "
            f"Wait for the company profile to fully load. "
        )

        if query_type == "credit_analysis":
            return (
                login_steps
                + "Navigate to the 'Financials' or 'Credit Analysis' section. "
                "Extract the credit and liquidity analysis data. "
                "Return a single JSON object with these fields: "
                "as_of (string, date of data), "
                "liquidity.cash_and_equivalents (number, USD millions), "
                "liquidity.short_term_investments (number, USD millions), "
                "liquidity.undrawn_revolver (number, USD millions), "
                "liquidity.total_liquidity (number, USD millions), "
                "liquidity.monthly_cash_burn_avg (number, USD millions), "
                "liquidity.runway_months (number), "
                "liquidity.current_ratio (number), "
                "liquidity.quick_ratio (number), "
                "leverage.total_debt (number, USD millions), "
                "leverage.net_debt (number, USD millions), "
                "leverage.debt_to_equity (number), "
                "leverage.net_leverage (string description), "
                "leverage.interest_coverage (string description), "
                "credit_score_implied (string, e.g. BB+), "
                "key_covenants_if_leveraged (array of strings)."
            )

        elif query_type == "peer_comparison":
            return (
                login_steps
                + "Navigate to the 'Benchmarking' or 'Peer Comparison' section. "
                "Extract the full peer comparison table. "
                "Return a JSON array where each object has: "
                "metric (string, metric name), "
                "acme (string, the target company's value for this metric), "
                "peer_median (string, peer median value), "
                "percentile (number, target company's percentile rank 0-100), "
                "signal (string, interpretation or signal text)."
            )

        elif query_type == "ownership_structure":
            return (
                login_steps
                + "Navigate to the 'Ownership' or 'Cap Table' or 'Shareholders' section. "
                "Extract the full ownership and cap table data. "
                "Return a single JSON object with: "
                "total_shares_fully_diluted (number), "
                "common_shares_outstanding (number), "
                "options_and_warrants (number), "
                "cap_table (array, each item: shareholder string, shares number, "
                "pct_basic number, pct_diluted number, investment_total_m number in USD millions, series string), "
                "liquidation_preferences (array, each item: series string, amount_m number in USD millions, preference string), "
                "total_liquidation_stack_m (number, total liquidation stack in USD millions)."
            )

        else:
            logger.warning("CapIQ: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Extract any available financial or market data about {company_name} "
                "as a JSON array of objects."
            )
