"""
QuickBooks Online connector.

Extracts profit & loss, balance sheet, and cash flow reports
from QuickBooks Online via TinyFish AI browser automation.

Authentication: Intuit QuickBooks Online — username + password.
Required credentials keys:
  - username     QuickBooks / Intuit email address
  - password     QuickBooks / Intuit account password
  - company_name Target company name (for context)

QuickBooks URL: https://app.qbo.intuit.com

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class QuickBooksConnector(BaseBrowserConnector):
    """Connector for QuickBooks Online data via TinyFish browser automation."""

    system_name = "quickbooks"
    category = "accounting"
    login_url = "https://accounts.intuit.com/app/sign-in"

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://accounts.intuit.com/app/sign-in. "
            f"Enter '{username}' in the email or username field and click 'Continue' or 'Next'. "
            f"Enter '{password}' in the password field and click 'Sign In'. "
            f"Wait for QuickBooks Online to load. If prompted to select a company, "
            f"select '{company_name}' or the most recently active company. "
            f"Wait for the QuickBooks dashboard to fully load. "
        )

        if query_type == "profit_loss":
            return (
                login_steps
                + "Navigate to Reports > Profit and Loss (or 'Income Statement'). "
                "Set the date range to the last 12 months. Run the report. "
                "Return a JSON object with: "
                "period (string, date range covered), "
                "total_revenue (number, total income in USD), "
                "cost_of_goods_sold (number, COGS in USD), "
                "gross_profit (number, in USD), "
                "gross_margin_pct (number, gross profit / revenue * 100), "
                "total_operating_expenses (number, in USD), "
                "ebitda (number, in USD), "
                "net_income (number, in USD), "
                "net_margin_pct (number, net income / revenue * 100), "
                "revenue_by_month (array of objects with month string and amount number)."
            )

        elif query_type == "balance_sheet":
            return (
                login_steps
                + "Navigate to Reports > Balance Sheet. "
                "Set to the most recent period. Run the report. "
                "Return a JSON object with: "
                "as_of (string, balance sheet date), "
                "total_assets (number, in USD), "
                "current_assets (number, in USD), "
                "cash_and_equivalents (number, in USD), "
                "accounts_receivable (number, in USD), "
                "total_liabilities (number, in USD), "
                "current_liabilities (number, in USD), "
                "accounts_payable (number, in USD), "
                "total_equity (number, in USD), "
                "retained_earnings (number, in USD), "
                "current_ratio (number, current assets / current liabilities), "
                "working_capital (number, current assets minus current liabilities, in USD)."
            )

        elif query_type == "cash_flow":
            return (
                login_steps
                + "Navigate to Reports > Statement of Cash Flows. "
                "Set the date range to the last 12 months. Run the report. "
                "Return a JSON object with: "
                "period (string, date range), "
                "operating_cash_flow (number, net cash from operating activities, in USD), "
                "investing_cash_flow (number, net cash from investing activities, in USD), "
                "financing_cash_flow (number, net cash from financing activities, in USD), "
                "net_change_in_cash (number, in USD), "
                "beginning_cash (number, in USD), "
                "ending_cash (number, in USD), "
                "free_cash_flow (number, operating cash flow minus capex, in USD), "
                "avg_monthly_burn (number, average monthly cash burn if negative, in USD), "
                "runway_months (number, ending cash divided by avg monthly burn if burning)."
            )

        else:
            logger.warning("QuickBooks: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Navigate to the Reports section and extract any available "
                f"financial report data about {company_name} as a JSON object."
            )
