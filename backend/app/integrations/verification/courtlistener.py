"""CourtListener public API client — free federal court records search."""
import httpx

COURTLISTENER_API = "https://www.courtlistener.com/api/rest/v4"


class CourtListenerClient:
    def __init__(self, api_token: str | None = None):
        headers = {"Accept": "application/json"}
        if api_token:
            headers["Authorization"] = f"Token {api_token}"
        self._headers = headers

    async def search_cases(self, company_name: str, max_results: int = 20) -> list[dict]:
        """Search court opinions for a company name. Returns list of case dicts."""
        params = {"q": company_name, "type": "o", "order_by": "score desc"}
        async with httpx.AsyncClient(timeout=15) as client:
            try:
                r = await client.get(
                    f"{COURTLISTENER_API}/search/",
                    params=params,
                    headers=self._headers,
                )
                r.raise_for_status()
                data = r.json()
                results = data.get("results", [])[:max_results]
                return [
                    {
                        "case_name": item.get("caseName", ""),
                        "court": item.get("court_id", ""),
                        "date_filed": item.get("dateFiled", ""),
                        "status": item.get("status", ""),
                        "url": f"https://www.courtlistener.com{item.get('absolute_url', '')}",
                        "description": item.get("snippet", "")[:500],
                        "external_id": str(item.get("id", "")),
                    }
                    for item in results
                ]
            except httpx.HTTPError:
                return []
