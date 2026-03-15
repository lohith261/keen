"""
LinkedIn Sales Navigator connector.

Extracts decision makers, company updates, and hiring trend data
from LinkedIn Sales Navigator via TinyFish AI browser automation.

Authentication: LinkedIn account with Sales Navigator subscription.
Required credentials keys:
  - username     LinkedIn email address
  - password     LinkedIn password
  - company_name Target company to research

LinkedIn URL: https://www.linkedin.com/sales/

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class SalesNavigatorConnector(BaseBrowserConnector):
    """Connector for LinkedIn Sales Navigator via TinyFish browser automation."""

    system_name = "sales_navigator"
    category = "intelligence"
    login_url = "https://www.linkedin.com/login"

    # ── Goal builder ──────────────────────────────────────────────────────────

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://www.linkedin.com/login. "
            f"Find the email or phone input field and enter '{username}'. "
            f"Find the password field and enter '{password}'. "
            f"Click the 'Sign in' button and wait for the LinkedIn home feed to load. "
            f"Navigate to https://www.linkedin.com/sales/home. "
            f"Wait for the Sales Navigator dashboard to fully load. "
            f"If a tour dialog or welcome popup appears, close or dismiss it. "
            f"Navigate to https://www.linkedin.com/sales/search/company. "
            f"Search for '{company_name}' in the company search box and click on the "
            f"correct company result to open their account page. "
            f"Wait for the company account page to fully load. "
        )

        if query_type == "decision_makers":
            return (
                login_steps
                + "Navigate to the 'People' or 'Contacts' section to see key decision makers. "
                "Filter for senior leadership: C-suite, VPs, and Directors. "
                "Extract all visible pages of results. "
                "Return a JSON array where each object has: "
                "name (string, full name), "
                "title (string, job title), "
                "linkedin_url (string, LinkedIn profile URL), "
                "connections (integer, number of connections), "
                "activity_score (string, activity level: Very High/High/Medium/Low), "
                "recent_posts (integer, number of posts in last 30 days), "
                "open_to_connect (boolean, whether they show as open to connect)."
            )

        elif query_type == "company_updates":
            return (
                login_steps
                + "Navigate to the 'Updates' or 'Activity' tab to see the company's recent LinkedIn posts. "
                "Scroll through and capture posts from the last 6 months. "
                "Return a JSON array where each object has: "
                "date (string, YYYY-MM-DD format), "
                "type (string, post category: Product Launch/Partnership/Award/Hiring/"
                "Thought Leadership/Customer Story/Other), "
                "content (string, description of the post content), "
                "engagement (integer, total reactions plus comments)."
            )

        elif query_type == "hiring_trends":
            return (
                login_steps
                + "Navigate to the 'Insights' or 'Headcount' section to see hiring trends. "
                "Return a single JSON object with: "
                "total_employees_linkedin (integer, total employees on LinkedIn), "
                "headcount_growth_12mo_pct (number, headcount growth % over last 12 months), "
                "open_roles_current (integer, number of open roles currently), "
                "open_roles_by_dept (object, department name to count mapping), "
                "recent_hires_30d (array, each item: title string, dept string — "
                "people who joined in the last 30 days), "
                "recent_departures_30d (array, each item: title string, dept string, "
                "note string — people who left in the last 30 days)."
            )

        else:
            logger.warning("Sales Navigator: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Extract any available company or people data about {company_name} "
                "as a JSON array of objects."
            )
