"""Technical DD service — wraps GitHubAnalyzer with engagement-level helpers."""
from app.integrations.github.client import GitHubAnalyzer

__all__ = ["GitHubAnalyzer", "analyze_repository"]


async def analyze_repository(repo_url: str, github_token: str | None = None) -> dict:
    """Convenience wrapper: create analyzer, run analysis, return result dict."""
    analyzer = GitHubAnalyzer(token=github_token)
    return await analyzer.analyze_repo(repo_url)
