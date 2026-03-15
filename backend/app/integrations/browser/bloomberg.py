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

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class BloombergConnector(BaseBrowserConnector):
    """Connector for Bloomberg Terminal data via TinyFish browser automation."""

    system_name = "bloomberg"
    category = "market_data"
    login_url = "https://bba.bloomberg.net"

    # ── Goal builder ──────────────────────────────────────────────────────────

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://bba.bloomberg.net. "
            f"Find the username or email input field and enter '{username}'. "
            f"If there is a 'Continue' or 'Next' button, click it. "
            f"Find the password field and enter '{password}'. "
            f"Click the 'Sign In' or 'Log In' or 'Submit' button and wait for "
            f"the Bloomberg dashboard to fully load. "
        )

        if query_type == "market_comps":
            return (
                login_steps
                + f"After login, navigate to https://bba.bloomberg.net/markets/equities. "
                f"Search for '{company_name}' and open its company profile page. "
                f"Find the 'Peer Analysis' or 'Comparable Companies' section. "
                f"Extract a list of comparable public companies. "
                f"Return a JSON array where each object has: "
                f"ticker (string), name (string), market_cap_m (number, market cap in USD millions), "
                f"ev_m (number, enterprise value in USD millions), "
                f"revenue_ttm_m (number, trailing 12-month revenue in USD millions), "
                f"ev_revenue (number, EV/Revenue multiple), "
                f"revenue_growth_pct (number, YoY revenue growth %), "
                f"gross_margin_pct (number, gross margin %), "
                f"rule_of_40 (number, Rule of 40 score)."
            )

        elif query_type == "industry_benchmarks":
            return (
                login_steps
                + f"After login, navigate to https://bba.bloomberg.net/markets/equities/sectors. "
                f"Find industry or sector benchmarks for the same segment as '{company_name}' "
                f"(e.g. B2B SaaS, enterprise software, or cloud software). "
                f"Return a single JSON object with: "
                f"segment (string), "
                f"median_revenue_growth_pct (number), "
                f"median_gross_margin_pct (number), "
                f"median_ev_revenue_multiple (number), "
                f"median_net_revenue_retention_pct (number), "
                f"median_cac_payback_months (number), "
                f"median_magic_number (number), "
                f"median_rule_of_40 (number), "
                f"top_quartile_ev_revenue (number), "
                f"bottom_quartile_ev_revenue (number), "
                f"peer_count (integer)."
            )

        elif query_type == "competitor_financials":
            return (
                login_steps
                + f"After login, navigate to the competitive landscape or comparable private "
                f"companies section for '{company_name}'. "
                f"Look for private company financials or deal comparables. "
                f"Return a JSON array where each object has: "
                f"company (string), "
                f"stage (string, e.g. Private/Public/Acquired), "
                f"est_revenue_m (number, estimated revenue in USD millions), "
                f"est_growth_pct (number, estimated growth %), "
                f"last_valuation_m (number, last known valuation in USD millions), "
                f"ev_revenue_implied (number, implied EV/Revenue multiple), "
                f"differentiator (string, key competitive differentiator)."
            )

        else:
            logger.warning("Bloomberg: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"After login, search for '{company_name}' and extract any available "
                f"financial or market data as a JSON array of objects."
            )
