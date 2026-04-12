"""
Pipeline for processing Wikipedia main page sections.

Takes scraped main page items, runs them through the LLM geotagger + geocoder,
and returns combined GeoJSON with source item metadata.

Each item is processed individually through the LLM to ensure accurate
source_item_index mapping on every pin.
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from lib.types.models import GeocodedTag, PlaceType, Relationship
from services.nlp.geotagger import extract_locations
from services.geocoder.geocode import geocode_tags
from services.scraper.main_page import (
    NewsItem,
    OtdEvent,
    DykFact,
    scrape_main_page,
)
from db.redis.landing_cache import get_landing_cached, set_landing_cached

logger = logging.getLogger(__name__)


@dataclass
class MainPageResult:
    section: str
    items: list[dict[str, Any]]
    geojson: dict[str, Any]
    total_items: int
    total_geocoded: int


def _make_feature(tag: GeocodedTag, source_index: int, source_label: str) -> dict[str, Any]:
    """Build a single GeoJSON Feature dict with source item metadata."""
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [tag.lng, tag.lat],
        },
        "properties": {
            "place_name": tag.place_name,
            "place_type": tag.place_type.value if isinstance(tag.place_type, PlaceType) else tag.place_type,
            "relationship": tag.relationship.value if isinstance(tag.relationship, Relationship) else tag.relationship,
            "reason": tag.reason,
            "source_sentence": tag.source_sentence,
            "geocoder": tag.geocoder,
            "source_item_index": source_index,
            "source_item_label": source_label,
        },
    }


async def _extract_and_geocode_item(
    index: int,
    text: str,
    title: str,
    label: str,
) -> list[dict[str, Any]]:
    """Run one item through LLM geotagger + geocoder, return GeoJSON features."""
    try:
        tags = await extract_locations(text, title)
    except Exception as e:
        logger.warning("LLM extraction failed for item %d: %s", index, e)
        return []

    if not tags:
        return []

    geocoded = await geocode_tags(tags)
    return [
        _make_feature(tag, index, label)
        for tag in geocoded
        if tag.lat is not None and tag.lng is not None
    ]


async def process_section_itn(items: list[NewsItem]) -> MainPageResult:
    """Process 'In the News' items — one LLM call per item."""
    all_features: list[dict] = []
    item_dicts: list[dict] = []

    for i, item in enumerate(items):
        features = await _extract_and_geocode_item(
            index=i,
            text=item.text,
            title=f"In the News — item {i + 1}",
            label=item.text[:100],
        )
        all_features.extend(features)
        item_dicts.append({"index": i, "text": item.text, "links": item.links})

    return MainPageResult(
        section="in_the_news",
        items=item_dicts,
        geojson={"type": "FeatureCollection", "features": all_features},
        total_items=len(items),
        total_geocoded=len(all_features),
    )


async def process_section_otd(events: list[OtdEvent]) -> MainPageResult:
    """Process 'On This Day' events — one LLM call per event."""
    all_features: list[dict] = []
    item_dicts: list[dict] = []

    for i, event in enumerate(events):
        features = await _extract_and_geocode_item(
            index=i,
            text=event.text,
            title=f"On This Day — {event.year}" if event.year else f"On This Day — item {i + 1}",
            label=event.text[:100],
        )
        all_features.extend(features)
        item_dicts.append({
            "index": i,
            "year": event.year,
            "text": event.text,
            "links": event.links,
        })

    return MainPageResult(
        section="on_this_day",
        items=item_dicts,
        geojson={"type": "FeatureCollection", "features": all_features},
        total_items=len(events),
        total_geocoded=len(all_features),
    )


async def process_section_dyk(facts: list[DykFact]) -> MainPageResult:
    """Process 'Did You Know' facts — one LLM call per fact."""
    all_features: list[dict] = []
    item_dicts: list[dict] = []

    for i, fact in enumerate(facts):
        features = await _extract_and_geocode_item(
            index=i,
            text=fact.text,
            title=f"Did You Know — fact {i + 1}",
            label=fact.text[:100],
        )
        all_features.extend(features)
        item_dicts.append({"index": i, "text": fact.text, "links": fact.links})

    return MainPageResult(
        section="did_you_know",
        items=item_dicts,
        geojson={"type": "FeatureCollection", "features": all_features},
        total_items=len(facts),
        total_geocoded=len(all_features),
    )


async def process_main_page_section(section: str) -> MainPageResult:
    """
    Scrape Wikipedia main page and process one section.

    section: "in_the_news" | "on_this_day" | "did_you_know"
    """
    # Check landing cache (separate Redis DB, 1-day TTL)
    cached = await get_landing_cached(section)
    if cached:
        logger.info("Landing cache hit for section: %s", section)
        return MainPageResult(**cached)

    # Scrape the main page
    sections = await scrape_main_page()

    # Process the requested section
    if section == "in_the_news":
        result = await process_section_itn(sections.in_the_news)
    elif section == "on_this_day":
        result = await process_section_otd(sections.on_this_day)
    elif section == "did_you_know":
        result = await process_section_dyk(sections.did_you_know)
    else:
        raise ValueError(f"Unknown section: {section}")

    # Cache in landing DB (1-day TTL)
    await set_landing_cached(section, {
        "section": result.section,
        "items": result.items,
        "geojson": result.geojson,
        "total_items": result.total_items,
        "total_geocoded": result.total_geocoded,
    })

    return result
