"""
Pipeline orchestrator.

Runs the full pipeline for a Wikipedia URL:
  1. Cache check  — Redis lookup by URL hash; cache hit returns immediately
  2. Scrape       — fetch and clean Wikipedia article
  3. Extract      — LLM geotagger (Gemini)
  4. Geocode      — Nominatim with rate limiting
  5. Persist      — write to PostgreSQL, cache in Redis
  6. Respond      — GeoJSON FeatureCollection
"""

import logging
import math
from dataclasses import dataclass, field
from typing import Any

from lib.types.models import GeocodedTag, PlaceType, Relationship, ScrapedArticle
from services.geocoder.geocode import geocode_tags
from services.nlp.geotagger import extract_locations
from services.scraper.wikipedia import scrape, url_hash as compute_hash

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    article: ScrapedArticle
    geocoded_tags: list[GeocodedTag] = field(default_factory=list)
    geojson: dict[str, Any] = field(default_factory=dict)
    total_extracted: int = 0
    total_geocoded: int = 0
    share_slug: str | None = None
    cache_hit: bool = False


def _build_geojson(tags: list[GeocodedTag]) -> dict[str, Any]:
    """Convert geocoded tags into a GeoJSON FeatureCollection."""
    features = []
    for tag in tags:
        if tag.lat is None or tag.lng is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [tag.lng, tag.lat],  # GeoJSON is [lng, lat]
            },
            "properties": {
                "place_name": tag.place_name,
                "place_type": tag.place_type.value if isinstance(tag.place_type, PlaceType) else tag.place_type,
                "relationship": tag.relationship.value if isinstance(tag.relationship, Relationship) else tag.relationship,
                "reason": tag.reason,
                "source_sentence": tag.source_sentence,
                "geocoder": tag.geocoder,
            },
        })

    return {
        "type": "FeatureCollection",
        "features": features,
    }


def _haversine_km(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance between two points in kilometres."""
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlng / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def _filter_outliers(tags: list[GeocodedTag], max_distance_km: float = 5000.0) -> list[GeocodedTag]:
    """
    Remove geocoded points that are geographic outliers.

    Computes the median centre of all geocoded points, then drops any point
    further than max_distance_km from that centre.  This catches
    mis-geocoded places like "North India" → North India, NY.
    """
    geocoded = [t for t in tags if t.lat is not None and t.lng is not None]
    if len(geocoded) < 3:
        return tags  # too few points to judge outliers

    lats = sorted(t.lat for t in geocoded)  # type: ignore[arg-type]
    lngs = sorted(t.lng for t in geocoded)  # type: ignore[arg-type]
    median_lat = lats[len(lats) // 2]
    median_lng = lngs[len(lngs) // 2]

    kept: list[GeocodedTag] = []
    for tag in tags:
        if tag.lat is None or tag.lng is None:
            kept.append(tag)  # un-geocoded tags pass through
            continue
        dist = _haversine_km(median_lat, median_lng, tag.lat, tag.lng)
        if dist <= max_distance_km:
            kept.append(tag)
        else:
            logger.warning(
                "Outlier removed: '%s' is %.0f km from cluster centre (limit %d km)",
                tag.place_name, dist, max_distance_km,
            )

    return kept


def _tags_to_dicts(tags: list[GeocodedTag]) -> list[dict]:
    """Serialise GeocodedTags for Redis cache storage."""
    return [t.model_dump(mode="json") for t in tags]


def _dicts_to_tags(dicts: list[dict]) -> list[GeocodedTag]:
    """Deserialise cached dicts back into GeocodedTag instances."""
    return [GeocodedTag(**d) for d in dicts]


async def process_page(url: str) -> PipelineResult:
    """
    Full pipeline: cache check → scrape → extract → geocode → persist → GeoJSON.
    """
    from db.redis.cache import get_cached_geotags, set_cached_geotags
    from db.postgres.queries import get_article_by_hash, save_article

    # Compute hash for cache lookup
    hash_val = compute_hash(url)

    # ── 1. Redis cache check ────────────────────────────────────────
    cached = await get_cached_geotags(hash_val)
    if cached is not None:
        logger.info("Cache hit for %s — skipping pipeline", url)
        tags = _dicts_to_tags(cached)
        geojson = _build_geojson(tags)

        # Retrieve share_slug from DB if available
        slug = None
        db_article = await get_article_by_hash(hash_val)
        if db_article:
            slug = db_article.share_slug

        return PipelineResult(
            article=ScrapedArticle(url=url, url_hash=hash_val, title=tags[0].place_name if tags else "Unknown"),
            geocoded_tags=tags,
            geojson=geojson,
            total_extracted=len(tags),
            total_geocoded=len(geojson["features"]),
            share_slug=slug,
            cache_hit=True,
        )

    # ── 2. Scrape ───────────────────────────────────────────────────
    logger.info("Scraping: %s", url)
    article = await scrape(url)

    # ── 3. Extract locations via LLM ────────────────────────────────
    logger.info("Extracting locations from '%s' (%d chars)", article.title, len(article.full_text))
    tags = await extract_locations(article.full_text, article.title)

    # ── 4. Geocode ──────────────────────────────────────────────────
    logger.info("Geocoding %d places", len(tags))
    geocoded = await geocode_tags(tags)

    # ── 5. Filter geographic outliers ──────────────────────────────
    geocoded = _filter_outliers(geocoded)

    # ── 6. Build GeoJSON ────────────────────────────────────────────
    geojson = _build_geojson(geocoded)
    total_geocoded = len(geojson["features"])

    # ── 7. Persist + cache (best-effort — don't fail the request) ──
    slug = None
    try:
        db_row = await save_article(article, geocoded)
        slug = db_row.share_slug
    except Exception as e:
        logger.warning("PostgreSQL persistence skipped: %s", e)

    try:
        await set_cached_geotags(article.url_hash, _tags_to_dicts(geocoded))
    except Exception as e:
        logger.warning("Redis caching skipped: %s", e)

    logger.info("Pipeline complete: %d extracted, %d geocoded", len(tags), total_geocoded)

    return PipelineResult(
        article=article,
        geocoded_tags=geocoded,
        geojson=geojson,
        total_extracted=len(tags),
        total_geocoded=total_geocoded,
        share_slug=slug,
    )
