"""
DemoConnector — a drop-in BaseConnector that returns fixture data for all
15 enterprise data sources, enabling full end-to-end pipeline testing
without any real credentials or network access.

Fixture files live in demo/fixtures/<source_id>.json.  Each file contains
keys matching the extraction types declared in DATA_SOURCES (e.g.
"pipeline_data", "revenue_data", …).  Querying an unknown extraction type
returns an empty list rather than raising.

Switch between demo and live mode by setting DEMO_MODE=true in .env.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.auth.manager import AuthFlowType, AuthSession
from app.integrations.base import BaseConnector

logger = logging.getLogger(__name__)

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


class DemoConnector(BaseConnector):
    """
    Connector that serves pre-built fixture data for a named data source.

    Usage::

        connector = DemoConnector("salesforce")
        session  = await connector.authenticate({})
        records  = await connector.extract({"type": "pipeline_data"})
    """

    system_name = "demo"
    category = "demo"

    def __init__(self, source_id: str, company_id: str = "", **kwargs: Any):
        super().__init__(**kwargs)
        self.source_id = source_id
        self._company_id = company_id
        self._fixture: dict = {}

    # ── BaseConnector interface ───────────────────────────

    async def authenticate(self, credentials: dict) -> AuthSession:  # noqa: ARG002
        """Load fixture file and return a synthetic auth session.

        Looks for company-specific fixtures first:
          fixtures/{company_id}/{source_id}.json
        Falls back to generic fixtures:
          fixtures/{source_id}.json
        """
        company_id = (self._company_id or "").lower().replace(" ", "_")
        company_path = _FIXTURES_DIR / company_id / f"{self.source_id}.json"
        generic_path  = _FIXTURES_DIR / f"{self.source_id}.json"

        fixture_path = company_path if (company_id and company_path.exists()) else generic_path

        if fixture_path.exists():
            with fixture_path.open() as fh:
                self._fixture = json.load(fh)
            logger.info("DemoConnector[%s]: loaded fixture from %s (%d keys)", self.source_id, fixture_path, len(self._fixture))
        else:
            logger.warning("DemoConnector[%s]: no fixture found at %s — returning empty data", self.source_id, fixture_path)
            self._fixture = {}

        session = AuthSession(
            system_name=f"demo_{self.source_id}",
            flow_type=AuthFlowType.API_KEY,
            session_data={"demo": "true", "source": self.source_id},
        )
        self.auth_session = session
        return session

    async def extract(self, query: dict) -> list[dict]:
        """
        Return fixture records for the requested extraction type.

        If the fixture value for the type is a list, it is returned directly.
        If it is a dict (e.g. a nested report), it is wrapped in a list.
        Unknown types return [].
        """
        extraction_type = query.get("type", "")

        if not self._fixture:
            # Lazy-load if authenticate was not called first
            await self.authenticate({})

        raw = self._fixture.get(extraction_type)

        if raw is None:
            logger.debug("DemoConnector[%s]: no fixture data for type=%r", self.source_id, extraction_type)
            return []

        if isinstance(raw, list):
            return raw

        # dict / scalar — wrap so callers always get a list
        return [raw]

    async def validate(self, data: list[dict]) -> dict:
        """Fixture data is always considered valid."""
        return {
            "total_records": len(data),
            "valid": True,
            "issues": [],
            "source": f"demo_{self.source_id}",
        }

    # ── Helpers ───────────────────────────────────────────

    def get_all_data(self) -> dict:
        """Return the entire fixture dict (all extraction types at once)."""
        return {k: v for k, v in self._fixture.items() if not k.startswith("_")}
