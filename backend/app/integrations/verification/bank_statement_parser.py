"""Bank statement PDF/TXT parser — extract transactions and detect anomalies."""
import io
import re
import statistics
from typing import Any

try:
    import pdfplumber
    _PDF_AVAILABLE = True
except ImportError:
    _PDF_AVAILABLE = False

# Regex for common bank statement transaction lines
# Matches: date, optional ref, description, amount
_TX_PATTERN = re.compile(
    r"(\d{1,2}[/\-]\d{1,2}[/\-]\d{2,4})"          # date
    r"[^\d\n]*"
    r"([\$\-\+]?\d{1,3}(?:,\d{3})*(?:\.\d{2})?)",  # amount
    re.MULTILINE,
)

_MONTH_PATTERN = re.compile(r"(\d{4})[/\-](\d{2})|(\w+)\s+(\d{4})")


class BankStatementParser:
    def parse(self, file_bytes: bytes, filename: str) -> dict[str, Any]:
        text = self._extract_text(file_bytes, filename)
        transactions = self.extract_transactions(text)
        monthly = self.compute_monthly_summary(transactions)
        anomalies = self.detect_anomalies(monthly)
        return {
            "page_count": text.count("\f") + 1 if text else 0,
            "transaction_count": len(transactions),
            "monthly_summary": monthly,
            "anomalies": anomalies,
            "raw_text_length": len(text),
        }

    def _extract_text(self, file_bytes: bytes, filename: str) -> str:
        if filename.lower().endswith(".pdf") and _PDF_AVAILABLE:
            with pdfplumber.open(io.BytesIO(file_bytes)) as pdf:
                return "\n".join(page.extract_text() or "" for page in pdf.pages)
        try:
            return file_bytes.decode("utf-8", errors="replace")
        except Exception:
            return ""

    def extract_transactions(self, text: str) -> list[dict[str, Any]]:
        txns = []
        for match in _TX_PATTERN.finditer(text):
            date_str, amount_str = match.group(1), match.group(2)
            try:
                amount = float(amount_str.replace(",", "").replace("$", ""))
                txns.append({"date": date_str, "amount": amount})
            except ValueError:
                continue
        return txns

    def compute_monthly_summary(self, transactions: list[dict]) -> dict[str, dict]:
        monthly: dict[str, dict] = {}
        for tx in transactions:
            # Simplistic month key from date string
            parts = re.split(r"[/\-]", tx["date"])
            if len(parts) >= 2:
                month_key = (
                    f"{parts[-1]}-{parts[0].zfill(2)}"
                    if len(parts[-1]) == 4
                    else tx["date"][:7]
                )
            else:
                month_key = "unknown"
            bucket = monthly.setdefault(
                month_key, {"credits": 0.0, "debits": 0.0, "net": 0.0}
            )
            if tx["amount"] >= 0:
                bucket["credits"] += tx["amount"]
            else:
                bucket["debits"] += abs(tx["amount"])
            bucket["net"] = bucket["credits"] - bucket["debits"]
        return monthly

    def detect_anomalies(self, monthly_summary: dict) -> list[str]:
        if len(monthly_summary) < 3:
            return []
        credits = [v["credits"] for v in monthly_summary.values() if v["credits"] > 0]
        if len(credits) < 3:
            return []
        med = statistics.median(credits)
        anomalies = []
        for month, vals in monthly_summary.items():
            if med > 0 and abs(vals["credits"] - med) / med > 0.25:
                pct = round((vals["credits"] - med) / med * 100, 1)
                direction = "above" if pct > 0 else "below"
                anomalies.append(
                    f"{month}: credits {abs(pct)}% {direction} median (${med:,.0f})"
                )
        return anomalies
