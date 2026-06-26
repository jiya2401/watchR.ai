# GitHub public REST API — free, 5000 req/hr with token.
# Detects org name automatically with multiple slug variants.

import re
from dataclasses import dataclass, field

import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from app.utils.logger import get_logger

log = get_logger(__name__)

GITHUB_API = "https://api.github.com"
GITHUB_HEADERS = {
    "Accept": "application/vnd.github.v3+json",
    "User-Agent": "WatchR-Intelligence-Agent/1.0",
}

# Manual overrides for companies with unusual GitHub org names
GITHUB_OVERRIDES: dict[str, str] = {
    "phonepe":    "PhonePe",
    "swiggy":     "Swiggy",
    "zomato":     "zomato",
    "cred":       "CRED-CLUB",
    "groww":      "Groww",
    "razorpay":   "razorpay",
    "meesho":     "Meesho",
    "flipkart":   "flipkart",
    "mmt":        "makemytrip",
    "dream11":    "dream11",
    "freshworks": "freshworks",
    "chargebee":  "chargebee",
    "postman":    "postmanlabs",
    "browserstack": "browserstack",
    "hasura":     "hasura",
}


@dataclass
class GithubInsights:
    org: str
    repos: list[dict] = field(default_factory=list)
    recent_commits: list[dict] = field(default_factory=list)
    languages: dict[str, int] = field(default_factory=dict)
    topics: list[str] = field(default_factory=list)
    total_stars: int = 0
    open_issues: int = 0
    error: str = ""


async def scrape_github(company: str) -> GithubInsights:
    """
    Fetch public GitHub data for a company.
    Returns GithubInsights with repos, commits, languages, topics.
    """
    name = company.lower().strip()
    slug = re.sub(r"[^a-z0-9]", "", name)

    # Build candidate org names to try
    candidates: list[str] = []

    # Check override registry first
    for key, org in GITHUB_OVERRIDES.items():
        if key in slug or slug in key:
            candidates.insert(0, org)

    # Common variations
    candidates += [
        slug,
        company.replace(" ", ""),
        company.replace(" ", "-"),
        f"{slug}hq",
        f"{slug}-engineering",
        f"{slug}inc",
        f"{slug}india",
    ]

    async with httpx.AsyncClient(
        headers=GITHUB_HEADERS, timeout=15, follow_redirects=True
    ) as client:

        # Find the right org
        org = await _find_org(client, candidates)
        if not org:
            log.warning("No GitHub org found for %s", company)
            return GithubInsights(org="", error="GitHub org not found")

        log.info("GitHub org found: %s", org)
        return await _collect_org_data(client, org)


async def _find_org(client: httpx.AsyncClient, candidates: list[str]) -> str | None:
    """Try each candidate org name and return the first valid one."""
    seen = set()
    for name in candidates:
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        try:
            r = await client.get(f"{GITHUB_API}/orgs/{name}")
            if r.status_code == 200:
                return name
        except Exception:
            continue
    return None


async def _collect_org_data(client: httpx.AsyncClient, org: str) -> GithubInsights:
    """Collect repos, commits, languages and topics for a GitHub org."""
    insights = GithubInsights(org=org)

    # Repos (sorted by recently updated)
    try:
        r = await client.get(
            f"{GITHUB_API}/orgs/{org}/repos",
            params={"sort": "updated", "per_page": 30, "type": "public"},
        )
        repos_raw = r.json() if r.status_code == 200 else []
    except Exception as e:
        log.error("Failed fetching repos for %s: %s", org, e)
        return insights

    all_languages: dict[str, int] = {}
    all_topics: list[str] = []

    for repo in repos_raw:
        insights.total_stars += repo.get("stargazers_count", 0)
        insights.open_issues += repo.get("open_issues_count", 0)
        all_topics.extend(repo.get("topics", []))

        # Language breakdown
        lang_url = repo.get("languages_url", "")
        if lang_url:
            try:
                lr = await client.get(lang_url)
                if lr.status_code == 200:
                    for lang, bytes_ct in lr.json().items():
                        all_languages[lang] = all_languages.get(lang, 0) + bytes_ct
            except Exception:
                pass

        insights.repos.append({
            "name":        repo["name"],
            "description": repo.get("description") or "",
            "language":    repo.get("language") or "",
            "stars":       repo.get("stargazers_count", 0),
            "updated":     repo.get("updated_at", ""),
            "topics":      repo.get("topics", []),
            "is_fork":     repo.get("fork", False),
        })

    # Recent commits from top 5 most recently updated repos
    for repo in repos_raw[:5]:
        if repo.get("fork"):
            continue
        try:
            cr = await client.get(
                f"{GITHUB_API}/repos/{org}/{repo['name']}/commits",
                params={"per_page": 8},
            )
            if cr.status_code == 200:
                for c in cr.json():
                    msg = c.get("commit", {}).get("message", "")
                    # Skip merge commits — they're noise
                    if msg.startswith("Merge"):
                        continue
                    insights.recent_commits.append({
                        "repo":    repo["name"],
                        "message": msg[:200],
                        "date":    c.get("commit", {}).get("author", {}).get("date", ""),
                    })
        except Exception:
            continue

    insights.languages = dict(
        sorted(all_languages.items(), key=lambda x: x[1], reverse=True)[:15]
    )
    insights.topics = list(set(all_topics))

    log.info(
        "GitHub collected for %s: %d repos, %d commits, %d languages",
        org, len(insights.repos), len(insights.recent_commits), len(insights.languages)
    )
    return insights
