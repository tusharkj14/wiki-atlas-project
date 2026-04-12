"""
Streaming pipeline — yields GeoJSON features one at a time as they are geocoded.

Used by the SSE endpoint to progressively load pins on the map.
"""

import logging
import math
from typing import Any, AsyncGenerator

from lib.types.models import GeocodedTag, GeoTag, PlaceType, Relationship
from services.geocoder.geocode import geocode_place
from services.nlp.geotagger import extract_locations
from services.scraper.wikipedia import scrape, url_hash as compute_hash
from db.redis.cache import get_cached_geotags, set_cached_geotags
from db.postgres.queries import get_article_by_hash, save_article

logger = logging.getLogger(__name__)


def _tag_to_feature(tag: GeocodedTag) -> dict[str, Any]:
    """Convert a single geocoded tag to a GeoJSON Feature."""
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
        },
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


async def stream_process_page(url: str) -> AsyncGenerator[dict[str, Any], None]:
    """
    Stream pipeline: yields SSE-ready dicts as pins are geocoded.

    Event types:
      - "meta"    : {title, url, url_hash, total_extracted}
      - "pin"     : a GeoJSON Feature
      - "done"    : {total_geocoded, share_slug, cache_hit}
      - "error"   : {message}
    """
    hash_val = compute_hash(url)

    # ── 1. Cache check ─────────────────────────────────────────────
    cached = await get_cached_geotags(hash_val)
    if cached is not None:
        logger.info("Stream: cache hit for %s", url)
        slug = None
        db_article = await get_article_by_hash(hash_val)
        if db_article:
            slug = db_article.share_slug

        title = cached[0].get("place_name", "Unknown") if cached else "Unknown"
        if db_article:
            title = db_article.title

        yield {"event": "meta", "data": {
            "title": title,
            "url": url,
            "url_hash": hash_val,
            "total_extracted": len(cached),
        }}

        count = 0
        for tag_dict in cached:
            tag = GeocodedTag(**tag_dict)
            if tag.lat is not None and tag.lng is not None:
                yield {"event": "pin", "data": _tag_to_feature(tag)}
                count += 1

        yield {"event": "done", "data": {
            "total_geocoded": count,
            "share_slug": slug,
            "cache_hit": True,
        }}
        return

    # ── 2. Scrape ──────────────────────────────────────────────────
    logger.info("Stream: scraping %s", url)
    article = await scrape(url)

    # ── 3. Extract locations ───────────────────────────────────────
    logger.info("Stream: extracting locations from '%s'", article.title)
    tags = await extract_locations(article.full_text, article.title)
    print(f"Extracted {len(tags)} tags from '{article.title}' - {tags}")

    yield {"event": "meta", "data": {
        "title": article.title,
        "url": article.url,
        "url_hash": article.url_hash,
        "total_extracted": len(tags),
    }}

    # ── 4. Geocode one by one, yielding each pin ──────────────────
    geocoded: list[GeocodedTag] = []
    geocoded_lats: list[float] = []
    geocoded_lngs: list[float] = []

    for tag in tags:
        coords = await geocode_place(tag.place_name, tag.country, tag.city)
        gt = GeocodedTag(
            place_name=tag.place_name,
            place_type=tag.place_type,
            relationship=tag.relationship,
            reason=tag.reason,
            source_sentence=tag.source_sentence,
            country=tag.country,
            city=tag.city,
            lat=coords[0] if coords else None,
            lng=coords[1] if coords else None,
            geocoder="nominatim" if coords else None,
        )
        geocoded.append(gt)

        if gt.lat is not None and gt.lng is not None:
            geocoded_lats.append(gt.lat)
            geocoded_lngs.append(gt.lng)
            yield {"event": "pin", "data": _tag_to_feature(gt)}

    # ── 5. Outlier filter (post-hoc info — client already has pins) ─
    # We skip outlier filtering for the stream since pins are already sent.
    # The non-streaming /process endpoint still filters.

    # ── 6. Persist + cache ─────────────────────────────────────────
    slug = None
    try:
        db_row = await save_article(article, geocoded)
        slug = db_row.share_slug
    except Exception as e:
        logger.warning("Stream: PostgreSQL persistence skipped: %s", e)

    try:
        await set_cached_geotags(article.url_hash, [t.model_dump(mode="json") for t in geocoded])
    except Exception as e:
        logger.warning("Stream: Redis caching skipped: %s", e)

    total_geocoded = sum(1 for t in geocoded if t.lat is not None)
    yield {"event": "done", "data": {
        "total_geocoded": total_geocoded,
        "share_slug": slug,
        "cache_hit": False,
    }}
