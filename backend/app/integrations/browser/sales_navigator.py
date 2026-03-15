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
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector
from app.integrations.browser.tinyfish import TinyFishSession

logger = logging.getLogger(__name__)


class SalesNavigatorConnector(BaseBrowserConnector):
    """Connector for LinkedIn Sales Navigator via TinyFish browser automation."""

    system_name = "sales_navigator"
    category = "intelligence"
    login_url = "https://www.linkedin.com/login"

    # ── Login flow ────────────────────────────────────────────────────────────

    async def _login(self, session: TinyFishSession, credentials: dict) -> None:
        """
        Authenticate to LinkedIn, then navigate to Sales Navigator.

        LinkedIn uses a standard username+password form at /login.
        After login, redirect to Sales Navigator at /sales/home.
        """
        username = credentials.get("username", "")
        password = credentials.get("password", "")

        if not username or not password:
            logger.warning("Sales Navigator: credentials missing username or password")
            return

        await session.act(
            "Find the email or phone input field and type the username",
            context={"username": username},
        )
        await session.act(
            "Find the password field and type the password",
            context={"password": password},
        )
        await session.act(
            "Click the 'Sign in' button and wait for the LinkedIn home feed to load"
        )

        # Navigate to Sales Navigator
        await session.navigate("https://www.linkedin.com/sales/home")
        await session.act(
            "Wait for the Sales Navigator dashboard to fully load. "
            "If a tour dialog appears, close or dismiss it."
        )

        logger.info("Sales Navigator: login and navigation completed")

    # ── Extraction ────────────────────────────────────────────────────────────

    async def _do_extract(
        self,
        session: TinyFishSession,
        query_type: str,
        company_name: str,
    ) -> list[dict]:
        extractors = {
            "decision_makers": self._extract_decision_makers,
            "company_updates": self._extract_company_updates,
            "hiring_trends": self._extract_hiring_trends,
        }
        extractor = extractors.get(query_type)
        if not extractor:
            logger.warning("Sales Navigator: unknown query type '%s'", query_type)
            return []
        return await extractor(session, company_name)

    async def _search_company(self, session: TinyFishSession, company_name: str) -> None:
        """Navigate to the target company's Sales Navigator account page."""
        await session.navigate("https://www.linkedin.com/sales/search/company")
        await session.act(
            f"Search for '{company_name}' in the company search box and click on "
            "the correct company result to open their account page"
        )
        await session.act("Wait for the company account page to fully load")

    async def _extract_decision_makers(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract key decision makers and their LinkedIn presence."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'People' or 'Contacts' section to see key decision makers at the company. "
            "Filter for senior leadership: C-suite, VPs, and Directors."
        )

        people = await session.extract(
            instruction=(
                "Extract the list of key decision makers and senior leaders. For each person include: "
                "full name, job title, LinkedIn profile URL, number of connections, "
                "activity level (Very High/High/Medium/Low), number of recent posts in last 30 days, "
                "and whether they are open to connect."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "title": {"type": "string"},
                        "linkedin_url": {"type": "string"},
                        "connections": {"type": "integer"},
                        "activity_score": {"type": "string"},
                        "recent_posts": {"type": "integer"},
                        "open_to_connect": {"type": "boolean"},
                    },
                },
            },
            paginate=True,
        )
        return people if isinstance(people, list) else [people]

    async def _extract_company_updates(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract recent company posts and announcements from LinkedIn."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Updates' or 'Activity' tab to see the company's recent LinkedIn posts"
        )

        updates = await session.extract(
            instruction=(
                "Extract the company's recent LinkedIn posts and updates from the last 6 months. "
                "For each post include: date (YYYY-MM-DD), type of update "
                "(Product Launch/Partnership/Award/Hiring/Thought Leadership/Customer Story/Other), "
                "content/description of the post, and engagement count (reactions + comments)."
            ),
            schema={
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "date": {"type": "string"},
                        "type": {"type": "string"},
                        "content": {"type": "string"},
                        "engagement": {"type": "integer"},
                    },
                },
            },
            paginate=True,
        )
        return updates if isinstance(updates, list) else [updates]

    async def _extract_hiring_trends(
        self, session: TinyFishSession, company_name: str
    ) -> list[dict]:
        """Extract headcount growth and open role data from LinkedIn."""
        await self._search_company(session, company_name)
        await session.act(
            "Navigate to the 'Insights' or 'Headcount' section to see hiring trends and employee data"
        )

        hiring = await session.extract(
            instruction=(
                "Extract the hiring and headcount data including: "
                "total employees on LinkedIn, headcount growth percentage over last 12 months, "
                "number of open roles currently, breakdown of open roles by department, "
                "list of recent hires in last 30 days (title and department), and "
                "list of recent departures in last 30 days (title, department, any notes)."
            ),
            schema={
                "type": "object",
                "properties": {
                    "total_employees_linkedin": {"type": "integer"},
                    "headcount_growth_12mo_pct": {"type": "number"},
                    "open_roles_current": {"type": "integer"},
                    "open_roles_by_dept": {"type": "object"},
                    "recent_hires_30d": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "dept": {"type": "string"},
                            },
                        },
                    },
                    "recent_departures_30d": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "dept": {"type": "string"},
                                "note": {"type": "string"},
                            },
                        },
                    },
                },
            },
        )
        return [hiring] if isinstance(hiring, dict) else hiring
