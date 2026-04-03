"""
Wikipedia article scraper.

Uses the Wikipedia REST API (/api/rest_v1/page/html/) to fetch article HTML,
then extracts clean text content: paragraphs, infobox data, and image captions
— stripping navigation, footers, references, and other chrome.
"""

import hashlib
import re
from urllib.parse import unquote, urlparse

import httpx
from bs4 import BeautifulSoup, Tag

from lib.types.models import ScrapedArticle

USER_AGENT = "WikiMap/1.0 (educational project; contact@example.com)"

# Sections that never contain useful geographic content
STRIP_SECTIONS = {
    "see also",
    "references",
    "external links",
    "further reading",
    "notes",
    "bibliography",
    "sources",
    "citations",
}

# Elements to remove before text extraction
STRIP_SELECTORS = [
    "table.sidebar",
    "sup.reference",
    "span.mw-editsection",
    ".mbox-small",
    ".ambox",
    ".dmbox",
    ".tmbox",
    ".ombox",
    ".cmbox",
    ".fmbox",
    ".imbox",
    "style",
    "script",
    "link",
    "meta",
]


def validate_wikipedia_url(url: str) -> str:
    """Validate and normalise a Wikipedia URL. Returns the cleaned URL."""
    parsed = urlparse(url)
    if not parsed.scheme:
        url = f"https://{url}"
        parsed = urlparse(url)

    hostname = parsed.hostname or ""
    if not hostname.endswith("wikipedia.org"):
        raise ValueError(f"Not a Wikipedia URL: {url}")

    if parsed.scheme not in ("http", "https"):
        raise ValueError(f"Invalid scheme: {parsed.scheme}")

    return url


def _extract_title_from_url(url: str) -> str:
    """Extract the article title from a Wikipedia URL path."""
    parsed = urlparse(url)
    path = parsed.path
    if "/wiki/" in path:
        return unquote(path.split("/wiki/")[-1])
    raise ValueError(f"Cannot extract article title from URL: {url}")


def url_hash(url: str) -> str:
    """SHA-256 hash of the URL, used as cache key."""
    return hashlib.sha256(url.encode()).hexdigest()


async def fetch_page(url: str) -> str:
    """Fetch article HTML via the Wikipedia REST API."""
    title = _extract_title_from_url(url)
    parsed = urlparse(url)
    lang_host = parsed.hostname
    api_url = f"https://{lang_host}/api/rest_v1/page/html/{title}"

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        resp = await client.get(api_url)
        resp.raise_for_status()
        return resp.text


def _extract_infobox(soup: BeautifulSoup) -> dict[str, str]:
    """Pull key-value pairs from the article's infobox table."""
    infobox: dict[str, str] = {}
    table = soup.find("table", class_="infobox")
    if not table or not isinstance(table, Tag):
        return infobox

    for row in table.find_all("tr"):
        header = row.find("th")
        data = row.find("td")
        if header and data:
            key = _clean_text(header.get_text(separator=" ", strip=True))
            val = _clean_text(data.get_text(separator=" ", strip=True))
            if key and val:
                infobox[key] = val

    return infobox


def _extract_captions(soup: BeautifulSoup) -> list[str]:
    """Extract image captions from figcaption and thumbcaption elements."""
    captions: list[str] = []
    seen: set[str] = set()

    for fig in soup.find_all(["figcaption", "div"]):
        if fig.name == "div" and "thumbcaption" not in (fig.get("class") or []):
            continue
        text = _clean_text(fig.get_text(separator=" ", strip=True))
        if text and text not in seen:
            captions.append(text)
            seen.add(text)

    return captions


def _clean_text(text: str) -> str:
    """Normalise whitespace and remove citation artefacts like [1], [23]."""
    text = re.sub(r"\[\d+\]", "", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def parse_article(html: str, url: str) -> ScrapedArticle:
    """Parse Wikipedia REST API HTML into a ScrapedArticle."""
    soup = BeautifulSoup(html, "html.parser")

    # --- title ---
    title_tag = soup.find("title")
    if title_tag:
        title = title_tag.get_text(strip=True)
    else:
        h1 = soup.find("h1")
        title = h1.get_text(strip=True) if h1 else _extract_title_from_url(url).replace("_", " ")

    # --- infobox (extract before stripping) ---
    infobox = _extract_infobox(soup)

    # --- captions (extract before stripping) ---
    captions = _extract_captions(soup)

    # --- remove noisy elements ---
    for selector in STRIP_SELECTORS:
        for el in soup.select(selector):
            el.decompose()

    # --- remove stripped sections entirely ---
    for section in soup.find_all("section"):
        heading = section.find(["h2", "h3"])
        if heading:
            heading_text = heading.get_text(strip=True).lower()
            if heading_text in STRIP_SECTIONS:
                section.decompose()

    # --- remove infobox (already extracted) ---
    for el in soup.find_all("table", class_="infobox"):
        el.decompose()

    # --- extract paragraphs ---
    paragraphs: list[str] = []
    for p in soup.find_all("p"):
        text = _clean_text(p.get_text(separator=" ", strip=True))
        if len(text) > 30:
            paragraphs.append(text)

    return ScrapedArticle(
        url=url,
        url_hash=url_hash(url),
        title=title,
        paragraphs=paragraphs,
        infobox=infobox,
        captions=captions,
    )


async def scrape(url: str) -> ScrapedArticle:
    """End-to-end: validate URL → fetch via REST API → parse → return ScrapedArticle."""
    url = validate_wikipedia_url(url)
    html = await fetch_page(url)
    return parse_article(html, url)
