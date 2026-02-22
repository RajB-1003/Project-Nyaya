"""
web_fetcher.py — Project Nyaya v2
Fetches live content from official Indian government legal portals.
All URLs verified working (HTTP 200, meaningful content).
Falls back gracefully (returns empty string) on any network/parse error.

Priority order per intent:
  - URLs are tried concurrently; up to 2 successes are fused as primary context.
  - If ALL fail → caller falls back to ChromaDB RAG automatically.

Caching: Successful responses cached for CACHE_TTL seconds (1 hour).
"""

import asyncio
import time
import logging
from typing import Optional

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger("nyaya.web_fetcher")

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

_cache: dict[str, tuple[str, float]] = {}
CACHE_TTL: int = 3600           # 1 hour
MIN_CONTENT_LEN: int = 100      # reduced from 300 — gov pages can be terse
MAX_PARAGRAPHS: int = 50        # max paragraphs to extract per page
MAX_CHARS_PER_SOURCE: int = 3500
FETCH_TIMEOUT: float = 7.0

# ---------------------------------------------------------------------------
# Verified government portal URL map  (tested 2026-02-22, all return HTTP 200)
# ---------------------------------------------------------------------------

GOVERNMENT_SOURCES: dict[str, list[dict]] = {
    "RTI": [
        {
            "url": "https://rtionline.gov.in/",
            "label": "RTI Online Portal — Official Portal (NIC / DoPT)",
        },
        {
            "url": "https://cic.gov.in/",
            "label": "Central Information Commission (CIC) — Official Portal",
        },
        {
            "url": "https://doj.gov.in/right-to-information",
            "label": "Department of Justice — Right to Information",
        },
        {
            "url": "https://www.indiacode.nic.in/handle/123456789/1879",
            "label": "India Code — Right to Information Act 2005 (Official Legislation Repository)",
        },
    ],
    "Domestic Violence": [
        {
            "url": "https://www.indiacode.nic.in/handle/123456789/15436",
            "label": "India Code — Protection of Women from Domestic Violence Act 2005",
        },
        {
            "url": "https://nalsa.gov.in/",
            "label": "National Legal Services Authority (NALSA) — Free Legal Aid",
        },
        {
            "url": "https://cic.gov.in/",
            "label": "Central Information Commission — Legal Resources",
        },
    ],
    "Divorce": [
        {
            "url": "https://www.indiacode.nic.in/handle/123456789/2055",
            "label": "India Code — Hindu Marriage Act 1955 (Official Legislation Repository)",
        },
        {
            "url": "https://nalsa.gov.in/",
            "label": "National Legal Services Authority (NALSA) — Free Legal Aid for Family Disputes",
        },
        {
            "url": "https://doj.gov.in/right-to-information",
            "label": "Department of Justice — Legal Resources",
        },
    ],
}

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-IN,en;q=0.9",
}


# ---------------------------------------------------------------------------
# HTML → clean text
# ---------------------------------------------------------------------------


def _extract_text(html: str) -> str:
    """Parse HTML, strip noise tags, return clean paragraph text."""
    soup = BeautifulSoup(html, "lxml")

    # Remove noise
    for tag in soup(["script", "style", "nav", "footer", "header",
                     "noscript", "aside", "form", "button", "iframe",
                     "meta", "link", "img", "figure"]):
        tag.decompose()

    # Prefer main content containers
    main = (
        soup.find("main")
        or soup.find("article")
        or soup.find(id="content")
        or soup.find(id="main-content")
        or soup.find(class_="content")
        or soup.find(class_="main-content")
        or soup.find(class_="node__content")
        or soup.find("body")
    )
    if not main:
        return ""

    texts: list[str] = []
    for tag in main.find_all(["p", "li", "h1", "h2", "h3", "h4", "td", "dd"]):
        t = tag.get_text(separator=" ", strip=True)
        # filter out very short fragments and navigation crumbs
        if len(t) > 40 and not t.startswith("Skip to"):
            texts.append(t)
        if len(texts) >= MAX_PARAGRAPHS:
            break

    return "\n".join(texts)


# ---------------------------------------------------------------------------
# Single URL fetch
# ---------------------------------------------------------------------------


async def _fetch_one(client: httpx.AsyncClient, source: dict) -> Optional[str]:
    """Fetch one URL. Returns formatted text or None on failure."""
    url = source["url"]
    label = source["label"]

    # Cache hit
    if url in _cache:
        text, ts = _cache[url]
        if time.time() - ts < CACHE_TTL:
            logger.info("Cache hit: %s (%d chars)", url, len(text))
            return f"[Source: {label}]\n{text}"

    try:
        logger.info("Fetching: %s", url)
        resp = await client.get(url, headers=_HEADERS)
        if resp.status_code != 200:
            logger.warning("HTTP %d: %s", resp.status_code, url)
            return None

        text = _extract_text(resp.text)
        if len(text) < MIN_CONTENT_LEN:
            logger.warning("Too short (%d chars): %s", len(text), url)
            return None

        text = text[:MAX_CHARS_PER_SOURCE]
        _cache[url] = (text, time.time())
        logger.info("OK — %d chars from %s", len(text), url)
        return f"[Source: {label}]\n{text}"

    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        logger.warning("Network error for %s: %s", url, exc)
        return None
    except Exception as exc:
        logger.warning("Unexpected error for %s: %s", url, exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


async def fetch_government_context(intent: str) -> tuple[str, list[str]]:
    """
    Fetch live legal content from official government portals for the given intent.

    Returns:
        (combined_text, sources_used)
        combined_text is "" if ALL fetches failed → caller falls back to RAG.
    """
    sources = GOVERNMENT_SOURCES.get(intent, [])
    if not sources:
        return "", []

    combined: list[str] = []
    sources_used: list[str] = []

    async with httpx.AsyncClient(
        timeout=httpx.Timeout(FETCH_TIMEOUT),
        follow_redirects=True,
    ) as client:
        # Fetch first 3 sources concurrently
        tasks = [_fetch_one(client, src) for src in sources[:3]]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        for src, result in zip(sources[:3], results):
            if isinstance(result, str) and result:
                combined.append(result)
                sources_used.append(src["label"])
            if len(combined) >= 2:
                break

    return "\n\n---\n\n".join(combined), sources_used


def get_available_sources(intent: str) -> list[str]:
    """Return all configured source URLs for a given intent."""
    return [s["url"] for s in GOVERNMENT_SOURCES.get(intent, [])]
