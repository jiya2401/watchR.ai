# Finds and scrapes engineering blogs for Indian startups.
# Strategy:
#   1. Check known blog registry (40+ Indian startups hardcoded)
#   2. Try common URL patterns (engineering.{name}.com etc)
#   3. Use Playwright to crawl blog index + scrape articles
#   4. Multiple content extraction strategies with fallbacks

import asyncio
import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PWTimeout

from app.scraper.base import HEADERS, polite_delay, clean_text
from app.utils.logger import get_logger

log = get_logger(__name__)

# Known Indian startup engineering blogs
KNOWN_BLOGS: dict[str, str] = {
    # Fintech
    "razorpay":    "https://engineering.razorpay.com",
    "paytm":       "https://blog.paytm.com/category/engineering",
    "phonepe":     "https://tech.phonepe.com",
    "cred":        "https://engineering.cred.club",
    "groww":       "https://tech.groww.in",
    "zerodha":     "https://zerodha.tech",
    "niyo":        "https://medium.com/niyo-tech",
    "slice":       "https://blog.sliceit.com/tag/engineering",
    "fi":          "https://fi.money/blog/posts?tag=engineering",
    "freo":        "https://medium.com/freo",

    # E-commerce / Quick commerce
    "flipkart":    "https://tech.flipkart.com",
    "meesho":      "https://engineering.meesho.com",
    "zepto":       "https://engineering.zeptonow.com",
    "blinkit":     "https://blinkit.com/blog",
    "swiggy":      "https://bytes.swiggy.com",
    "zomato":      "https://blog.zomato.com/tagged/engineering",
    "nykaa":       "https://medium.com/nykaa-tech",
    "myntra":      "https://medium.com/myntra-engineering",

    # SaaS / Developer tools
    "freshworks":  "https://medium.com/freshworks-developer-blog",
    "chargebee":   "https://www.chargebee.com/blog/category/engineering",
    "postman":     "https://blog.postman.com",
    "browserstack":"https://www.browserstack.com/blog/category/engineering",
    "hasura":      "https://hasura.io/blog/tagged/engineering",
    "clevertap":   "https://clevertap.com/blog/category/engineering",
    "setu":        "https://setu.co/blog",
    "glean":       "https://medium.com/glean-data",

    # Travel / Mobility
    "ola":         "https://tech.olacabs.com",
    "rapido":      "https://medium.com/rapido-labs",
    "redbus":      "https://tech.redbus.in",
    "mmt":         "https://medium.com/makemytrip-engineering",

    # Edtech / Other
    "byjus":       "https://medium.com/byju-s-engineering",
    "unacademy":   "https://medium.com/unacademy-engineering",
    "sharechat":   "https://engineering.sharechat.com",
    "dailyhunt":   "https://medium.com/dailyhunt-tech",
    "dream11":     "https://medium.com/dream11-tech-blog",
    "mpl":         "https://medium.com/mobile-premier-league-engineers",

    # Infra / Cloud
    "dgraph":      "https://dgraph.io/blog",
    "druva":       "https://www.druva.com/blog/category/engineering",
    "mindtickle":  "https://www.mindtickle.com/blog/engineering",
}

# URL patterns to probe when company not in known list
BLOG_PATTERNS = [
    "https://engineering.{slug}.com",
    "https://tech.{slug}.com",
    "https://blog.{slug}.com",
    "https://{slug}.com/blog",
    "https://{slug}.com/engineering",
    "https://{slug}.com/tech-blog",
    "https://medium.com/{slug}-engineering",
    "https://medium.com/{slug}-tech",
]

# CSS selectors that reliably find article links across different blog platforms
ARTICLE_LINK_SELECTORS = [
    "article a[href]",
    "h1 a[href]", "h2 a[href]", "h3 a[href]",
    ".post-title a", ".article-title a", ".entry-title a",
    ".post-card a", ".blog-post a", ".post-preview a",
    "[class*='post'] a[href]", "[class*='article'] a[href]",
    "[class*='blog'] a[href]",
    "a[href*='/blog/']", "a[href*='/engineering/']",
    "a[href*='/tech/']", "a[href*='/posts/']",
]

# Selectors for article body content
BODY_SELECTORS = [
    "article", ".post-content", ".article-body",
    ".entry-content", ".post-body", ".blog-post-content",
    "[class*='post-content']", "[class*='article-content']",
    "main .content", "main", ".content",
]


@dataclass
class BlogArticle:
    url: str
    title: str
    content: str
    date: str = ""
    tags: list[str] = field(default_factory=list)
    word_count: int = 0


async def find_blog_url(company: str) -> str | None:
    """
    Find blog URL for a company.
    Checks known registry first, then probes URL patterns.
    """
    name = company.lower().strip()
    slug = re.sub(r"[^a-z0-9]", "", name)

    # 1. Exact match in known registry
    for key, url in KNOWN_BLOGS.items():
        if key == name or key == slug:
            log.info("Known blog found for %s → %s", company, url)
            return url

    # 2. Partial match (e.g. "Razorpay India" → "razorpay")
    for key, url in KNOWN_BLOGS.items():
        if key in slug or slug in key:
            log.info("Partial blog match for %s → %s", company, url)
            return url

    # 3. Probe common patterns
    async with httpx.AsyncClient(
        headers=HEADERS, timeout=8, follow_redirects=True
    ) as client:
        for pattern in BLOG_PATTERNS:
            url = pattern.format(slug=slug)
            try:
                r = await client.get(url)
                if r.status_code == 200 and len(r.text) > 500:
                    log.info("Blog found via pattern probe: %s", url)
                    return url
            except Exception:
                continue

    log.warning("No blog found for %s", company)
    return None


async def scrape_blog(company: str, max_articles: int = 12) -> list[BlogArticle]:
    # Main entry point. Finds blog URL and scrapes articles.
    # Returns list of BlogArticle objects.

    blog_url = await find_blog_url(company)
    if not blog_url:
        return []

    log.info("Scraping blog for %s: %s", company, blog_url)

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
            ],
        )
        context = await browser.new_context(
            user_agent=HEADERS["User-Agent"],
            viewport={"width": 1280, "height": 800},
            java_script_enabled=True,
        )

        # Block images/fonts to speed up scraping
        await context.route(
            "**/*.{png,jpg,jpeg,gif,webp,svg,woff,woff2,ttf,eot}",
            lambda route: route.abort(),
        )

        page = await context.new_page()

        article_links = await _get_article_links(page, blog_url)
        article_links = list(dict.fromkeys(article_links))[:max_articles]
        log.info("Found %d article links for %s", len(article_links), company)

        articles = []
        for url in article_links:
            try:
                article = await _scrape_article(page, url)
                if article and article.word_count > 100:
                    articles.append(article)
                    log.info("✓ [%d words] %s", article.word_count, article.title[:60])
                await polite_delay(1.0, 2.5)
            except PWTimeout:
                log.warning("Timeout scraping: %s", url)
            except Exception as e:
                log.warning("Failed scraping %s: %s", url, str(e)[:80])

        await browser.close()

    log.info("Scraped %d/%d articles for %s", len(articles), len(article_links), company)
    return articles


async def _get_article_links(page: Page, blog_url: str) -> list[str]:
    """Extract article links from blog index page."""
    try:
        await page.goto(blog_url, wait_until="domcontentloaded", timeout=30000)
        await page.wait_for_timeout(2500)

        # Try to load more articles (some blogs have infinite scroll / load more)
        for _ in range(2):
            try:
                btn = await page.query_selector(
                    "button:has-text('Load more'), button:has-text('More posts'), "
                    "[class*='load-more']"
                )
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1500)
            except Exception:
                break

        content = await page.content()
    except Exception as e:
        log.error("Failed loading blog index %s: %s", blog_url, e)
        return []

    soup = BeautifulSoup(content, "lxml")
    base = f"{urlparse(blog_url).scheme}://{urlparse(blog_url).netloc}"
    blog_domain = urlparse(blog_url).netloc
    links: set[str] = set()

    for selector in ARTICLE_LINK_SELECTORS:
        for tag in soup.select(selector):
            href = tag.get("href", "").strip()
            if not href or href in ("#", "/", ""):
                continue
            # Resolve relative URLs
            full = urljoin(base, href) if href.startswith("/") else href
            parsed = urlparse(full)
            # Must be on same domain and not the index itself
            if parsed.netloc == blog_domain and full.rstrip("/") != blog_url.rstrip("/"):
                links.add(full)

    return list(links)


async def _scrape_article(page: Page, url: str) -> BlogArticle | None:
    """Scrape a single article and extract clean content."""
    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
    await page.wait_for_timeout(1000)
    content = await page.content()

    soup = BeautifulSoup(content, "lxml")

    # Remove noise elements
    for noise in soup(["script", "style", "nav", "footer", "header",
                       "aside", "iframe", ".sidebar", ".cookie-banner",
                       ".newsletter", ".subscribe", ".comments", ".share-buttons"]):
        noise.decompose()

    # Title
    title = ""
    for sel in ["h1", ".post-title", ".article-title", "title"]:
        t = soup.select_one(sel)
        if t and t.get_text(strip=True):
            title = t.get_text(strip=True)
            break

    # Date
    date = ""
    for sel in ["time[datetime]", ".date", ".published", ".post-date", "time"]:
        d = soup.select_one(sel)
        if d:
            date = d.get("datetime", "") or d.get_text(strip=True)
            break

    # Tags
    tags = [t.get_text(strip=True) for t in soup.select(
        ".tag, .label, [rel='tag'], .category, [class*='tag']"
    )][:6]

    # Content — try selectors in order of specificity
    body = None
    for sel in BODY_SELECTORS:
        candidate = soup.select_one(sel)
        if candidate:
            text = candidate.get_text(separator="\n", strip=True)
            if len(text) > 300:
                body = candidate
                break

    if not body:
        body = soup.find("body")

    raw_text = body.get_text(separator="\n", strip=True) if body else ""
    text = clean_text(raw_text)
    word_count = len(text.split())

    return BlogArticle(
        url=url,
        title=title,
        content=text,
        date=date,
        tags=tags,
        word_count=word_count,
    )
