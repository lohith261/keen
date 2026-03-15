"""
SAP ERP connector.

Extracts financial statements, cost centers, and purchase orders
from SAP via TinyFish AI browser automation (SAP Fiori / SAP S4HANA web).

Authentication: SAP — username + password.
Required credentials keys:
  - username      SAP User ID / login name
  - password      SAP password
  - instance_url  SAP Fiori Launchpad URL (e.g. https://company.sapbydstate.com/ui)
  - company_name  Target company name (for context)
  - client        SAP client number (optional, defaults to 100)

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class SAPConnector(BaseBrowserConnector):
    """Connector for SAP ERP data via TinyFish browser automation."""

    system_name = "sap"
    category = "erp"
    login_url = "https://www.sap.com/products/erp.html"  # overridden by instance_url

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        instance_url = credentials.get("instance_url", "")
        client = credentials.get("client", "100")

        if not instance_url:
            logger.warning("SAP: no instance_url provided — extraction will likely fail")
            instance_url = "https://my.sap.com"

        login_steps = (
            f"Go to {instance_url}. "
            f"If a client number field is shown, enter '{client}'. "
            f"Enter '{username}' in the User field or username field. "
            f"Enter '{password}' in the Password field. "
            f"Click 'Log On' or 'Sign In' and wait for the SAP Fiori Launchpad or "
            f"SAP Easy Access menu to fully load. "
        )

        if query_type == "financial_statements":
            return (
                login_steps
                + "Navigate to the Financial Reporting or Accounting app. "
                "Find the Profit and Loss Statement or Income Statement and Balance Sheet. "
                "Set the fiscal year to the most recent completed year and current YTD. "
                "Return a JSON object with: "
                "fiscal_year (string), "
                "period (string, e.g. Jan-Dec 2024), "
                "income_statement.total_revenue (number, in USD or functional currency), "
                "income_statement.cogs (number), "
                "income_statement.gross_profit (number), "
                "income_statement.operating_expenses (number), "
                "income_statement.ebit (number, earnings before interest and tax), "
                "income_statement.ebitda (number), "
                "income_statement.net_income (number), "
                "balance_sheet.total_assets (number), "
                "balance_sheet.total_liabilities (number), "
                "balance_sheet.total_equity (number), "
                "balance_sheet.cash (number), "
                "balance_sheet.total_debt (number), "
                "currency (string, 3-letter currency code)."
            )

        elif query_type == "cost_centers":
            return (
                login_steps
                + "Navigate to Controlling > Cost Center Accounting > Cost Center Report. "
                "Extract the cost center hierarchy and spend by department. "
                "Return a JSON array where each object represents a cost center and has: "
                "cost_center_id (string), "
                "cost_center_name (string), "
                "cost_center_group (string, parent grouping), "
                "responsible_person (string), "
                "actual_spend_ytd (number, actual costs year-to-date), "
                "budget_ytd (number, budgeted costs year-to-date), "
                "variance_usd (number, actual minus budget), "
                "variance_pct (number, variance as percentage of budget), "
                "currency (string)."
            )

        elif query_type == "purchase_orders":
            return (
                login_steps
                + "Navigate to Materials Management > Purchasing > Purchase Order or "
                "the Purchase Orders app in Fiori. "
                "Filter for open purchase orders from the last 12 months. "
                "Return a JSON array where each object represents a PO and has: "
                "po_number (string), "
                "vendor_name (string), "
                "vendor_id (string), "
                "creation_date (string, YYYY-MM-DD), "
                "delivery_date (string, YYYY-MM-DD), "
                "total_value (number, PO total in functional currency), "
                "currency (string), "
                "status (string, e.g. Open/Partially Delivered/Closed), "
                "line_items (array of objects with: item_description string, "
                "quantity number, unit_price number, total number). "
                "Include up to 50 most recent POs."
            )

        else:
            logger.warning("SAP: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Navigate to the reporting section and extract any available "
                f"financial or operational data as a JSON object."
            )
