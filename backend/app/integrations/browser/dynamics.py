"""
Microsoft Dynamics 365 connector.

Extracts sales pipeline, customer segments, and revenue forecast data
from Microsoft Dynamics 365 via TinyFish AI browser automation.

Authentication: Microsoft 365 — username + password (Azure AD / work account).
Required credentials keys:
  - username     Microsoft 365 work email
  - password     Microsoft 365 password
  - instance_url Dynamics 365 instance URL (e.g. https://org.crm.dynamics.com)
  - company_name Target company name (for context)

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class DynamicsConnector(BaseBrowserConnector):
    """Connector for Microsoft Dynamics 365 data via TinyFish browser automation."""

    system_name = "dynamics"
    category = "crm"
    login_url = "https://login.microsoftonline.com"

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        instance_url = credentials.get("instance_url", "")

        dynamics_url = instance_url or "https://dynamics.microsoft.com/en-us/signin/"

        login_steps = (
            f"Go to https://login.microsoftonline.com. "
            f"Enter '{username}' as the email or phone and click 'Next'. "
            f"Enter '{password}' as the password and click 'Sign in'. "
            f"If prompted 'Stay signed in?', click 'No'. "
            f"Navigate to {dynamics_url} if not already there. "
            f"Wait for Microsoft Dynamics 365 Sales to fully load. "
        )

        if query_type == "sales_pipeline":
            return (
                login_steps
                + "Navigate to Sales > Opportunities or the Pipeline view. "
                "Look for a funnel or pipeline chart showing opportunities by stage. "
                "Extract the full pipeline breakdown. "
                "Return a JSON object with: "
                "as_of (string, current date YYYY-MM-DD), "
                "total_pipeline_value_usd (number, total open opportunity value), "
                "total_open_opportunities (integer, count of open opps), "
                "avg_deal_size_usd (number), "
                "avg_sales_cycle_days (number), "
                "stages (array of objects with: "
                "stage_name string, opportunity_count integer, "
                "total_value_usd number, avg_probability_pct number, "
                "avg_age_days number), "
                "top_opportunities (array of the 5 largest open opportunities, each with: "
                "name string, account string, estimated_value_usd number, "
                "stage string, close_date string, probability_pct number)."
            )

        elif query_type == "customer_segments":
            return (
                login_steps
                + "Navigate to Sales > Accounts or Customer Service > Accounts. "
                "Look for account segmentation by industry, size, or tier. "
                "If available, go to Reports or Dashboards for customer segment data. "
                "Return a JSON array where each object represents a customer segment and has: "
                "segment_name (string, e.g. Enterprise/Mid-Market/SMB or by industry), "
                "account_count (integer), "
                "total_arr_usd (number, total annual recurring revenue from this segment), "
                "avg_arr_per_account_usd (number), "
                "avg_nrr_pct (number, net revenue retention if available), "
                "churn_rate_pct (number, annual churn rate if available), "
                "top_accounts (array of strings, top 3 account names)."
            )

        elif query_type == "revenue_forecast":
            return (
                login_steps
                + "Navigate to Sales > Forecasts or the Forecast dashboard. "
                "Find the current quarter and next quarter revenue forecast. "
                "Return a JSON object with: "
                "current_period (string, e.g. Q1 2025), "
                "quota_usd (number, total sales quota for period), "
                "committed_forecast_usd (number, committed/won deals), "
                "best_case_forecast_usd (number, best case scenario), "
                "pipeline_coverage_ratio (number, pipeline value / quota), "
                "won_to_date_usd (number, closed-won revenue so far this period), "
                "attainment_pct (number, won to date / quota * 100), "
                "forecast_by_rep (array of objects with: "
                "rep_name string, quota_usd number, committed_usd number, "
                "best_case_usd number, won_usd number)."
            )

        else:
            logger.warning("Dynamics: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Navigate to Sales dashboards and extract any available "
                f"CRM or sales data as a JSON object."
            )
