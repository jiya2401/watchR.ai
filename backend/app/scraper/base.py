# Shared utilities for all scrapers. 
import asyncio
import random
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception_type, before_sleep_log
)
import httpx
import logging 
 
log = logging.getLogger(__name__)

# Realistic browser headers — reduces blocking
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
}


def retry_on_network(func):
    # Decorator: retry up to 3 times on network errors with backoff
    return retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, asyncio.TimeoutError)),
        before_sleep=before_sleep_log(log, logging.WARNING),
        reraise=True,
    )(func)


async def polite_delay(min_s: float = 1.0, max_s: float = 3.0) -> None:
    # Random delay between requests — avoids rate limiting
    await asyncio.sleep(random.uniform(min_s, max_s))


def clean_text(text: str, max_chars: int = 8000) -> str:
    # Normalize whitespace and cap length
    import re
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    text = text.strip()
    return text[:max_chars]
