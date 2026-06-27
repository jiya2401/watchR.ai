"""
app/celery_tasks/scraping_tasks.py
Background task: scrape blog + GitHub → embed everything → return summary.
Triggered by LangGraph's trigger_scrape node.
"""
import asyncio
from app.celery_app import celery_app
from app.utils.logger import get_logger

log = get_logger(__name__)


def _async(coro):
    """Run coroutine from sync Celery task."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(
    bind=True,
    name="app.celery_tasks.scraping_tasks.run_full_scrape",
    queue="scraping",
    max_retries=1,
    soft_time_limit=480,
)
def run_full_scrape(self, company: str, job_id: str) -> dict:
    """
    Full data collection pipeline:
    1. Scrape engineering blog (Playwright)
    2. Fetch GitHub data (REST API)
    3. Embed all content into ChromaDB
    Returns summary dict that LangGraph await_scrape node uses.
    """
    from app.scraper.blog_scraper import scrape_blog
    from app.scraper.github_scraper import scrape_github
    from app.rag.embedder import embed_and_store

    result = {
        "blog_count": 0,
        "github": {},
        "chunks_embedded": 0,
        "sources": [],
    }

    # ── Step 1: Blog scraping ─────────────────────────────────
    log.info("Starting blog scrape for %s", company)
    try:
        articles = _async(scrape_blog(company, max_articles=12))
        result["blog_count"] = len(articles)

        if articles:
            result["sources"].append("blog")
            total_chunks = 0
            for article in articles:
                n = embed_and_store(
                    company=company,
                    source="blog",
                    url=article.url,
                    title=article.title,
                    content=article.content,
                    metadata={
                        "date":       article.date,
                        "tags":       ",".join(article.tags),
                        "word_count": str(article.word_count),
                    },
                )
                total_chunks += n

            result["chunks_embedded"] += total_chunks
            log.info(
                "Blog: %d articles → %d chunks embedded for %s",
                len(articles), total_chunks, company
            )
        else:
            log.warning("No blog articles found for %s", company)

    except Exception as e:
        log.error("Blog scrape failed for %s: %s", company, e)

    # ── Step 2: GitHub scraping ───────────────────────────────
    log.info("Starting GitHub scrape for %s", company)
    try:
        github = _async(scrape_github(company))

        if not github.error:
            result["sources"].append("github")
            result["github"] = {
                "org":        github.org,
                "topics":     github.topics,
                "languages":  github.languages,
                "total_stars":github.total_stars,
                "open_issues":github.open_issues,
                "repo_count": len(github.repos),
            }

            # Embed individual repos
            for repo in github.repos:
                content = (
                    f"Repository: {repo['name']}\n"
                    f"Description: {repo['description']}\n"
                    f"Primary language: {repo['language']}\n"
                    f"Topics: {', '.join(repo['topics'])}\n"
                    f"Stars: {repo['stars']}\n"
                    f"Last updated: {repo['updated']}"
                )
                embed_and_store(
                    company=company,
                    source="github",
                    url=f"https://github.com/{github.org}/{repo['name']}",
                    title=repo["name"],
                    content=content,
                )

            # Embed recent commits as a batch narrative
            if github.recent_commits:
                commit_narrative = (
                    f"Recent engineering activity at {company} (from GitHub commits):\n\n"
                    + "\n".join([
                        f"[{c['date'][:10]}] [{c['repo']}] {c['message']}"
                        for c in github.recent_commits
                    ])
                )
                embed_and_store(
                    company=company,
                    source="github",
                    url=f"https://github.com/{github.org}",
                    title=f"{company} recent commits",
                    content=commit_narrative,
                )

            # Embed language + topic summary
            lang_summary = (
                f"Technology profile for {company} based on GitHub:\n"
                f"Primary languages: {', '.join(list(github.languages.keys())[:10])}\n"
                f"Repository topics: {', '.join(github.topics[:20])}\n"
                f"Total public stars: {github.total_stars}\n"
                f"Open issues: {github.open_issues}"
            )
            embed_and_store(
                company=company,
                source="github",
                url=f"https://github.com/{github.org}",
                title=f"{company} tech profile",
                content=lang_summary,
            )

            log.info(
                "GitHub: %d repos, %d commits for %s",
                len(github.repos), len(github.recent_commits), company
            )
        else:
            log.warning("GitHub: %s", github.error)

    except Exception as e:
        log.error("GitHub scrape failed for %s: %s", company, e)

    # ── Step 3: Save raw summary to MongoDB ───────────────────
    try:
        from pymongo import MongoClient
        from datetime import datetime
        from app.config import get_settings
        s = get_settings()
        client = MongoClient(s.mongo_uri, serverSelectionTimeoutMS=3000)
        db = client[s.mongo_db]
        db.raw_data.insert_one({
            "company":    company,
            "job_id":     job_id,
            "source":     "scrape_summary",
            "url":        "",
            "content":    str(result),
            "scraped_at": datetime.utcnow(),
        })
        client.close()
    except Exception as e:
        log.warning("Raw data save failed: %s", e)

    log.info("Scrape complete for %s: %s", company, result)
    return result
