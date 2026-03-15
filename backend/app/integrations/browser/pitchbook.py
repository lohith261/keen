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

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class PitchBookConnector(BaseBrowserConnector):
    """Connector for PitchBook data via TinyFish browser automation."""

    system_name = "pitchbook"
    category = "market_data"
    login_url = "https://pitchbook.com/login"

    # ── Goal builder ──────────────────────────────────────────────────────────

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://pitchbook.com/login. "
            f"Find the email input field and enter '{username}'. "
            f"Find the password field and enter '{password}'. "
            f"Click the 'Sign In' or 'Log In' button and wait for the PitchBook dashboard to load. "
            f"Use the search bar at the top to search for '{company_name}' and click the "
            f"correct company in the results list. "
            f"Wait for the company profile to fully load. "
        )

        if query_type == "deal_comps":
            return (
                login_steps
                + "Navigate to the 'Deals' or 'Comparable Transactions' section. "
                "Filter for M&A deals in the same sector from the past 3 years. "
                "Extract the list of comparable M&A transactions. "
                "Return a JSON array where each object has: "
                "target (string, target company name), "
                "acquirer (string, acquirer name), "
                "deal_date (string, YYYY-MM-DD format), "
                "deal_value_m (number, deal value in USD millions), "
                "revenue_at_deal_m (number, revenue at time of deal in USD millions), "
                "ev_revenue (number, EV/Revenue multiple), "
                "arr_at_deal_m (number, ARR at deal in USD millions), "
                "growth_pct (number, revenue growth % at time of deal), "
                "deal_type (string, e.g. Buyout/Strategic Acquisition/Platform Roll-up). "
                "Include all pages of results."
            )

        elif query_type == "valuation_multiples":
            return (
                login_steps
                + "Navigate to the 'Valuation' or 'Multiples' section of the company profile. "
                "Look for benchmark valuation data for the company's sector and ARR range. "
                "Return a single JSON object with: "
                "segment (string, segment description), "
                "sample_size (integer, number of comparable deals), "
                "arr_range (string, e.g. '$10M-$50M ARR'), "
                "ev_arr_median (number, median EV/ARR multiple), "
                "ev_arr_mean (number, mean EV/ARR multiple), "
                "ev_arr_25th_percentile (number), "
                "ev_arr_75th_percentile (number), "
                "ev_arr_top_decile (number), "
                "growth_premium_per_10pct (number, EV/ARR premium per 10% additional growth), "
                "gross_margin_premium_per_5pct (number, premium per 5% gross margin improvement), "
                "nrr_premium_above_120pct (number, premium for NRR > 120%), "
                "implied_range_for_target.low (number, implied valuation low in USD millions), "
                "implied_range_for_target.mid (number, implied valuation mid in USD millions), "
                "implied_range_for_target.high (number, implied valuation high in USD millions), "
                "implied_range_for_target.basis (string, valuation basis description)."
            )

        elif query_type == "fund_performance":
            return (
                login_steps
                + "Navigate to the 'Investors' section of the company profile to see VC/PE backers. "
                "For each lead investor, click through to view their fund performance metrics. "
                "Return a JSON array where each object represents a fund and has: "
                "fund (string, fund name), "
                "vintage (integer, vintage year), "
                "irr_pct (number, IRR as a percentage), "
                "moic (number, multiple on invested capital), "
                "dpi (number, distributions to paid-in ratio), "
                "fund_size_m (number, fund size in USD millions), "
                "notable_exits (array of strings, list of notable portfolio exits). "
                "Include all investors shown on the page."
            )

        else:
            logger.warning("PitchBook: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Extract any available deal or investment data about {company_name} "
                "as a JSON array of objects."
            )
