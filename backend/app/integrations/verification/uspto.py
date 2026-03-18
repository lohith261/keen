"""USPTO Patent Full-Text and Trademark API clients."""
import httpx

PATENT_API = "https://developer.uspto.gov/ibd-api/v1/patent/application"
TRADEMARK_SEARCH = "https://developer.uspto.gov/trademark/v1/basicSearch"


class USPTOClient:
    async def search_patents(self, assignee: str, max_results: int = 20) -> list[dict]:
        params = {"assigneeEntityName": assignee, "start": 0, "rows": max_results}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.get(PATENT_API, params=params)
                r.raise_for_status()
                data = r.json()
                patents = (
                    data.get("results", {}).get("patent", [])
                    if isinstance(data.get("results"), dict)
                    else []
                )
                return [
                    {
                        "patent_number": p.get("patentNumber", ""),
                        "title": p.get("inventionTitle", ""),
                        "filing_date": p.get("filingDate", ""),
                        "status": p.get("applicationStatusCode", ""),
                        "assignee": p.get("assigneeEntityName", assignee),
                        "external_id": p.get("patentNumber", ""),
                    }
                    for p in patents
                ]
            except (httpx.HTTPError, KeyError, TypeError):
                return []

    async def search_trademarks(self, company_name: str) -> list[dict]:
        # Trademark API endpoint — returns [] if unavailable
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.get(f"{TRADEMARK_SEARCH}/text={company_name}")
                if r.status_code != 200:
                    return []
                data = r.json()
                marks = data.get("hits", {}).get("hits", [])
                return [
                    {
                        "mark": m.get("_source", {}).get("markLiteralElements", ""),
                        "status": m.get("_source", {}).get(
                            "markCurrentStatusExternalDescriptionText", ""
                        ),
                        "owner": m.get("_source", {}).get("businessName", ""),
                        "external_id": m.get("_id", ""),
                    }
                    for m in marks[:20]
                ]
            except (httpx.HTTPError, KeyError):
                return []
