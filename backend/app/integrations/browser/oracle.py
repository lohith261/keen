"""
Oracle ERP Cloud connector.

Extracts GL journal entries, AR aging, and AP aging data
from Oracle Fusion Cloud ERP via TinyFish AI browser automation.

Authentication: Oracle Cloud — username + password.
Required credentials keys:
  - username      Oracle Cloud login (email or username)
  - password      Oracle Cloud password
  - instance_url  Oracle Cloud ERP URL (e.g. https://company.fa.em2.oraclecloud.com)
  - company_name  Target company name (for context)

TinyFish Architecture: Each extract() call sends a single natural-language
goal that includes login + navigation + extraction.  No persistent session.
"""

from __future__ import annotations

import logging

from app.integrations.browser.base import BaseBrowserConnector

logger = logging.getLogger(__name__)


class OracleConnector(BaseBrowserConnector):
    """Connector for Oracle Cloud ERP data via TinyFish browser automation."""

    system_name = "oracle"
    category = "erp"
    login_url = "https://cloud.oracle.com"

    def _build_goal(self, query_type: str, company_name: str, credentials: dict) -> str:
        username = credentials.get("username", "")
        password = credentials.get("password", "")
        instance_url = credentials.get("instance_url", "")

        if not instance_url:
            logger.warning("Oracle: no instance_url provided")
            instance_url = "https://cloud.oracle.com"

        login_steps = (
            f"Go to {instance_url}. "
            f"Enter '{username}' in the user name or email field. "
            f"Enter '{password}' in the password field. "
            f"Click 'Sign In' and wait for the Oracle Cloud home page to load. "
            f"Navigate to the ERP Cloud or Financials module. "
            f"Wait for the ERP dashboard to fully load. "
        )

        if query_type == "gl_entries":
            return (
                login_steps
                + "Navigate to General Ledger > Journals > Manage Journals or "
                "the Account Analysis report. "
                "Filter for journal entries from the last 3 months. "
                "Return a JSON array where each object represents a journal entry line and has: "
                "journal_name (string), "
                "journal_date (string, YYYY-MM-DD), "
                "period (string, accounting period), "
                "account_code (string, GL account number), "
                "account_description (string, GL account name), "
                "debit_amount (number, in functional currency), "
                "credit_amount (number), "
                "entity (string, legal entity or business unit), "
                "cost_center (string), "
                "description (string, journal line description), "
                "status (string, Posted/Unposted/Approved). "
                "Include up to 200 most recent entries."
            )

        elif query_type == "ar_aging":
            return (
                login_steps
                + "Navigate to Accounts Receivable > Receivables > Aging or "
                "Reports > Aging by Customer. "
                "Pull the current AR aging report as of today. "
                "Return a JSON object with: "
                "as_of (string, report date YYYY-MM-DD), "
                "total_ar_balance (number, total outstanding AR in functional currency), "
                "current_usd (number, invoices not yet due), "
                "days_1_30 (number, invoices 1-30 days past due), "
                "days_31_60 (number, 31-60 days), "
                "days_61_90 (number, 61-90 days), "
                "days_91_120 (number, 91-120 days), "
                "over_120_days (number, 120+ days past due), "
                "currency (string), "
                "top_overdue_customers (array of objects with: customer_name string, "
                "balance_usd number, days_overdue integer, for the 10 largest overdue balances)."
            )

        elif query_type == "ap_aging":
            return (
                login_steps
                + "Navigate to Accounts Payable > Payables > Aging or "
                "Reports > AP Aging by Supplier. "
                "Pull the current AP aging report as of today. "
                "Return a JSON object with: "
                "as_of (string, report date YYYY-MM-DD), "
                "total_ap_balance (number, total AP outstanding in functional currency), "
                "current_usd (number, invoices not yet due), "
                "days_1_30 (number, invoices 1-30 days past due), "
                "days_31_60 (number, 31-60 days past due), "
                "days_61_90 (number, 61-90 days past due), "
                "over_90_days (number, 90+ days past due), "
                "currency (string), "
                "top_suppliers (array of objects with: supplier_name string, "
                "balance_usd number, payment_terms string, overdue_usd number, "
                "for the 10 largest AP balances)."
            )

        else:
            logger.warning("Oracle: unknown query type '%s'", query_type)
            return (
                login_steps
                + f"Navigate to the financial reporting section and extract any available "
                f"ERP data as a JSON object."
            )
