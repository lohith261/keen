"""
ZoomInfo connector.

Extracts org chart, employee count trends, and tech stack data
from ZoomInfo via TinyFish AI browser automation.

Authentication: ZoomInfo — username + password.
Required credentials keys:
  - username     ZoomInfo login email
  - password     ZoomInfo account password
  - company_name Target company to research

ZoomInfo URL: https://app.zoominfo.com

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class ZoomInfoConnector(BaseBrowserConnector):
    """Connector for ZoomInfo data via TinyFish browser automation."""

    system_name = "zoominfo"
    category = "intelligence"
    login_url = "https://app.zoominfo.com/#/login"

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        login_steps = (
            f"Go to https://app.zoominfo.com/#/login. "
            f"Enter '{username}' in the email field. "
            f"Enter '{password}' in the password field. "
            f"Click 'Log In' or 'Sign In' and wait for the ZoomInfo dashboard to load. "
            f"Use the search bar to search for company '{company_name}' and click the correct result. "
            f"Wait for the company profile page to fully load. "
        )

        if query_type == "org_chart":
            return (
                login_steps
                + "Navigate to the 'People' or 'Org Chart' section of the company profile. "
                "Extract the organizational hierarchy showing key leaders and their teams. "
                "Return a JSON array where each object represents a person and has: "
                "name (string, full name), "
                "title (string, job title), "
                "department (string, department or function), "
                "level (string, e.g. C-Suite/VP/Director/Manager/Individual Contributor), "
                "email (string, work email if available), "
                "phone (string, direct phone if available), "
                "reports_to (string, manager's name or empty if top of org), "
                "linkedin_url (string, LinkedIn profile URL if shown)."
            )

        elif query_type == "employee_count_trends":
            return (
                login_steps
                + "Navigate to the 'Signals' or 'Insights' or 'Company Info' section "
                "that shows headcount and employee growth data. "
                "Return a JSON object with: "
                "current_employee_count (integer, total employees), "
                "employee_count_range (string, e.g. '500-1000'), "
                "headcount_growth_1yr_pct (number, % growth over last 12 months), "
                "headcount_growth_2yr_pct (number, % growth over last 24 months), "
                "department_breakdown (object, department name to headcount mapping), "
                "recent_hiring_signals (array of strings, recent job posting themes), "
                "recent_layoff_signals (array of strings, any layoff news or signals), "
                "employee_count_by_quarter (array of objects with quarter string and count integer, last 8 quarters)."
            )

        elif query_type == "tech_stack":
            return (
                login_steps
                + "Navigate to the 'Technologies' or 'Tech Stack' section of the company profile. "
                "Extract all technology products and tools the company uses. "
                "Return a JSON array where each object represents a technology and has: "
                "name (string, product/tool name), "
                "vendor (string, company that makes the tool), "
                "category (string, e.g. CRM/ERP/Marketing Automation/Analytics/Cloud Infrastructure/Security/HR), "
                "first_detected (string, approximate date first seen, YYYY-MM format), "
                "confidence (string, High/Medium/Low). "
                "Include all technologies visible across all categories."
            )

        else:
            logger.warning("ZoomInfo: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Extract any available company intelligence data about {company_name} "
                "as a JSON object."
            )
