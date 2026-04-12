"""
Wikipedia main page section scraper.

Fetches https://en.wikipedia.org/wiki/Main_Page and extracts items from:
  - "In the news"
  - "On this day"
  - "Did you know..."
"""

import logging
from dataclasses import dataclass

import httpx
from bs4 import BeautifulSoup, Tag

logger = logging.getLogger(__name__)

USER_AGENT = "WikiAtlas/1.0 (educational project; contact@example.com)"
MAIN_PAGE_URL = "https://en.wikipedia.org/wiki/Main_Page"


@dataclass
class NewsItem:
    text: str
    links: list[str]  # Wikipedia URLs referenced


@dataclass
class OtdEvent:
    year: str
    text: str
    links: list[str]


@dataclass
class DykFact:
    text: str
    links: list[str]


@dataclass
class MainPageSections:
    in_the_news: list[NewsItem]
    on_this_day: list[OtdEvent]
    did_you_know: list[DykFact]


def _absolute_wiki_url(href: str) -> str:
    """Convert a relative /wiki/ link to an absolute URL."""
    if href.startswith("/wiki/"):
        return f"https://en.wikipedia.org{href}"
    return href


def _extract_links(element: Tag) -> list[str]:
    """Extract Wikipedia article URLs from an element."""
    links = []
    for a in element.find_all("a", href=True):
        href = a["href"]
        if isinstance(href, list):
            href = href[0]
        if href.startswith("/wiki/") and ":" not in href.split("/wiki/")[1]:
            links.append(_absolute_wiki_url(href))
    return links


def _parse_in_the_news(soup: BeautifulSoup) -> list[NewsItem]:
    """Extract items from the 'In the news' section."""
    items: list[NewsItem] = []

    # The section is identified by #mp-itn (or similar id patterns)
    itn = soup.find(id="mp-itn")
    if not itn:
        # Fallback: look for heading text
        for h2 in soup.find_all("h2"):
            if "in the news" in h2.get_text(strip=True).lower():
                itn = h2.find_parent("div")
                break

    if not itn:
        logger.warning("Could not find 'In the news' section")
        return items

    # Get the list items
    for li in itn.find_all("li"):
        # Skip nested lists (sub-items)
        if li.find_parent("li"):
            continue
        text = li.get_text(separator=" ", strip=True)
        if text and len(text) > 15:
            links = _extract_links(li)
            items.append(NewsItem(text=text, links=links))

    return items


def _parse_on_this_day(soup: BeautifulSoup) -> list[OtdEvent]:
    """Extract events from the 'On this day' section."""
    events: list[OtdEvent] = []

    otd = soup.find(id="mp-otd")
    if not otd:
        for h2 in soup.find_all("h2"):
            if "on this day" in h2.get_text(strip=True).lower():
                otd = h2.find_parent("div")
                break

    if not otd:
        logger.warning("Could not find 'On this day' section")
        return events

    for li in otd.find_all("li"):
        if li.find_parent("li"):
            continue
        text = li.get_text(separator=" ", strip=True)
        if not text or len(text) < 10:
            continue

        # Extract year from the beginning (e.g., "1865 – ...")
        year = ""
        parts = text.split(" – ", 1)
        if len(parts) == 2 and parts[0].strip().isdigit():
            year = parts[0].strip()
        elif len(parts) == 2:
            # Try en-dash variant
            parts2 = text.split(" - ", 1)
            if len(parts2) == 2 and parts2[0].strip().isdigit():
                year = parts2[0].strip()

        links = _extract_links(li)
        events.append(OtdEvent(year=year, text=text, links=links))

    return events


def _parse_did_you_know(soup: BeautifulSoup) -> list[DykFact]:
    """Extract facts from the 'Did you know...' section."""
    facts: list[DykFact] = []

    dyk = soup.find(id="mp-dyk")
    if not dyk:
        for h2 in soup.find_all("h2"):
            if "did you know" in h2.get_text(strip=True).lower():
                dyk = h2.find_parent("div")
                break

    if not dyk:
        logger.warning("Could not find 'Did you know' section")
        return facts

    for li in dyk.find_all("li"):
        if li.find_parent("li"):
            continue
        text = li.get_text(separator=" ", strip=True)
        if text and len(text) > 15:
            links = _extract_links(li)
            facts.append(DykFact(text=text, links=links))

    return facts


async def fetch_main_page() -> str:
    """Fetch the Wikipedia main page HTML."""
    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        follow_redirects=True,
        timeout=30.0,
    ) as client:
        resp = await client.get(MAIN_PAGE_URL)
        resp.raise_for_status()
        return resp.text


async def scrape_main_page() -> MainPageSections:
    """Scrape all three sections from Wikipedia's main page."""
    html = await fetch_main_page()
    soup = BeautifulSoup(html, "html.parser")

    return MainPageSections(
        in_the_news=_parse_in_the_news(soup),
        on_this_day=_parse_on_this_day(soup),
        did_you_know=_parse_did_you_know(soup),
    )
