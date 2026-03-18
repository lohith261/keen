"""GitHub API client for technical due diligence."""
import math
from datetime import datetime, timezone

import httpx

GITHUB_API = "https://api.github.com"


class GitHubAnalyzer:
    def __init__(self, token: str | None = None):
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if token:
            self.headers["Authorization"] = f"Bearer {token}"

    def _parse_repo_url(self, repo_url: str) -> tuple[str, str]:
        """Extract owner/repo from GitHub URL or 'owner/repo' string."""
        url = (
            repo_url.rstrip("/")
            .replace("https://github.com/", "")
            .replace("http://github.com/", "")
        )
        parts = url.split("/")
        if len(parts) < 2:
            raise ValueError(f"Cannot parse repo URL: {repo_url}")
        return parts[0], parts[1].removesuffix(".git")

    async def analyze_repo(self, repo_url: str) -> dict:
        owner, repo = self._parse_repo_url(repo_url)
        async with httpx.AsyncClient(timeout=20, headers=self.headers) as client:
            repo_r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}")
            repo_r.raise_for_status()
            repo_data = repo_r.json()

            lang_r = await client.get(f"{GITHUB_API}/repos/{owner}/{repo}/languages")
            languages = lang_r.json() if lang_r.status_code == 200 else {}

            contrib_r = await client.get(
                f"{GITHUB_API}/repos/{owner}/{repo}/contributors",
                params={"per_page": 100, "anon": "false"},
            )
            contributors = contrib_r.json() if contrib_r.status_code == 200 else []

            open_issues = repo_data.get("open_issues_count", 0)

            commit_velocity = await self._get_commit_velocity(client, owner, repo)

        bus_factor = self._compute_bus_factor(contributors)
        health_score = self.compute_health_score(
            repo_data, contributors, languages, commit_velocity
        )

        return {
            "repo_url": repo_url,
            "language_stats": languages,
            "contributor_count": len(contributors),
            "bus_factor": bus_factor,
            "commit_velocity": commit_velocity,
            "open_issues_count": open_issues,
            "security_vulnerabilities": [],
            "dependency_risks": [],
            "health_score": health_score,
            "status": "ready",
        }

    async def _get_commit_velocity(
        self, client: httpx.AsyncClient, owner: str, repo: str
    ) -> float:
        r = await client.get(
            f"{GITHUB_API}/repos/{owner}/{repo}/stats/commit_activity"
        )
        if r.status_code != 200:
            return 0.0
        weeks = r.json()
        if not weeks:
            return 0.0
        recent = weeks[-13:]  # last ~3 months
        total = sum(w.get("total", 0) for w in recent)
        return round(total / len(recent), 2)

    def _compute_bus_factor(self, contributors: list[dict]) -> int:
        if not contributors:
            return 0
        totals = [c.get("contributions", 0) for c in contributors]
        grand_total = sum(totals)
        if grand_total == 0:
            return 0
        running = 0
        for i, t in enumerate(sorted(totals, reverse=True), start=1):
            running += t
            if running / grand_total >= 0.5:
                return i
        return len(totals)

    def compute_health_score(
        self,
        repo_data: dict,
        contributors: list,
        languages: dict,
        commit_velocity: float,
    ) -> float:
        score = 0.0
        # Stars (log scale, max 20)
        stars = repo_data.get("stargazers_count", 0)
        score += min(20.0, math.log1p(stars) * 3)
        # Contributors
        n_contrib = len(contributors)
        score += 20.0 if n_contrib > 5 else (10.0 if n_contrib >= 3 else 0.0)
        # Commit velocity
        score += 20.0 if commit_velocity > 5 else (10.0 if commit_velocity >= 1 else 0.0)
        # Recency of last push
        pushed_at = repo_data.get("pushed_at", "")
        if pushed_at:
            try:
                delta = (
                    datetime.now(timezone.utc)
                    - datetime.fromisoformat(pushed_at.replace("Z", "+00:00"))
                ).days
                score += 20.0 if delta < 30 else (10.0 if delta < 90 else 0.0)
            except ValueError:
                pass
        # Open issues ratio
        issues = repo_data.get("open_issues_count", 0)
        forks = repo_data.get("forks_count", 1) or 1
        ratio = issues / forks
        score += 20.0 if ratio < 0.1 else (10.0 if ratio < 0.5 else 0.0)
        return round(min(100.0, score), 1)
