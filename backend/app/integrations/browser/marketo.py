"""
Marketo connector.

Extracts lead scoring, email campaign metrics, and attribution data
from Marketo via TinyFish AI browser automation.

Authentication: Marketo — username + password (Marketo Engage web UI).
Required credentials keys:
  - username     Marketo login email
  - password     Marketo account password
  - instance_url Marketo instance URL (e.g. https://app-abc123.marketo.com)
  - company_name Target company name (for context)

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class MarketoConnector(BaseBrowserConnector):
    """Connector for Marketo Engage data via TinyFish browser automation."""

    system_name = "marketo"
    category = "marketing"
    login_url = "https://app.marketo.com"

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        instance_url = credentials.get("instance_url", "https://app.marketo.com")

        login_steps = (
            f"Go to {instance_url}. "
            f"Enter '{username}' in the email or login field. "
            f"Enter '{password}' in the password field. "
            f"Click 'Sign In' or 'Log In' and wait for the Marketo Engage dashboard to load. "
        )

        if query_type == "lead_scoring":
            return (
                login_steps
                + "Navigate to Lead Management or Database. "
                "Find the lead scoring model or smart list that shows lead scores. "
                "Extract the lead score distribution and scoring model details. "
                "Return a JSON object with: "
                "score_model_name (string), "
                "total_scored_leads (integer), "
                "score_distribution (array of objects with range string like '0-25', "
                "count integer, and pct number), "
                "avg_lead_score (number), "
                "mql_threshold (integer, score at which leads become MQL), "
                "top_scoring_behaviors (array of strings, highest-point scoring actions), "
                "score_decay_rules (array of strings, negative scoring behaviors), "
                "leads_above_mql_threshold (integer, count of leads ready to pass to sales)."
            )

        elif query_type == "email_metrics":
            return (
                login_steps
                + "Navigate to Email > Email Performance Report or Analytics > Email Performance. "
                "Set the date range to the last 90 days. "
                "Extract email campaign performance data. "
                "Return a JSON array where each object represents an email campaign/program and has: "
                "program_name (string), "
                "email_name (string), "
                "send_date (string, YYYY-MM-DD), "
                "emails_sent (integer), "
                "emails_delivered (integer), "
                "delivery_rate_pct (number), "
                "open_rate_pct (number, unique opens / delivered), "
                "click_rate_pct (number, unique clicks / delivered), "
                "click_to_open_rate_pct (number, clicks / opens), "
                "unsubscribe_rate_pct (number), "
                "bounce_rate_pct (number, hard + soft bounces / sent)."
            )

        elif query_type == "attribution_data":
            return (
                login_steps
                + "Navigate to Analytics > Program Performance or Revenue Cycle Analytics. "
                "Look for multi-touch attribution or program-to-revenue reports. "
                "Return a JSON object with: "
                "model_name (string, attribution model being used), "
                "period (string, reporting period), "
                "total_pipeline_influenced_usd (number, total pipeline attributed to marketing), "
                "total_revenue_influenced_usd (number, total closed-won revenue attributed), "
                "top_programs (array of objects with: program_name string, "
                "pipeline_influenced_usd number, revenue_influenced_usd number, "
                "program_roi_pct number, cost_per_mql_usd number), "
                "channel_breakdown (array of objects with: channel string, "
                "pipeline_pct number, revenue_pct number)."
            )

        else:
            logger.warning("Marketo: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Navigate to Analytics and extract any available marketing performance data "
                f"as a JSON object."
            )
