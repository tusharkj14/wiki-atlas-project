"""
Redis cache layer.

Keys:
  geotags:{url_hash}      — full JSON tag set, TTL 7 days
  geocode:{place_name}     — individual geocode result, permanent
"""

import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

GEOTAG_TTL = 60 * 60 * 24 * 7  # 7 days

_redis = None


async def get_redis():
    """Lazy-initialise and return the async Redis client."""
    global _redis
    if _redis is not None:
        return _redis

    redis_url = os.getenv("REDIS_URL")
    if not redis_url:
        return None

    import redis.asyncio as aioredis
    _redis = aioredis.from_url(redis_url, decode_responses=True)
    return _redis


async def close_redis():
    """Close the Redis connection pool."""
    global _redis
    if _redis is not None:
        await _redis.aclose()
        _redis = None


# ── Geotag cache (full pipeline result) ────────────────────────────

async def get_cached_geotags(url_hash: str) -> Optional[list[dict]]:
    """Return cached geotag JSON for a URL hash, or None on miss."""
    r = await get_redis()
    if r is None:
        return None
    raw = await r.get(f"geotags:{url_hash}")
    if raw is None:
        return None
    logger.info("Cache HIT for geotags:%s", url_hash)
    return json.loads(raw)


async def set_cached_geotags(url_hash: str, tags: list[dict]) -> None:
    """Cache the full geotag set for a URL hash with 7-day TTL."""
    r = await get_redis()
    if r is None:
        return
    await r.set(f"geotags:{url_hash}", json.dumps(tags), ex=GEOTAG_TTL)
    logger.info("Cached %d geotags for %s (TTL=%ds)", len(tags), url_hash, GEOTAG_TTL)


# ── Geocode cache (individual place → coords) ─────────────────────

async def get_cached_geocode(place_name: str) -> Optional[tuple[float, float]]:
    """Return cached (lat, lng) for a place name, or None on miss."""
    r = await get_redis()
    if r is None:
        return None
    raw = await r.get(f"geocode:{place_name}")
    if raw is None:
        return None
    data = json.loads(raw)
    if data is None:
        return None
    return (data["lat"], data["lng"])


async def set_cached_geocode(place_name: str, lat: float, lng: float) -> None:
    """Cache a geocode result permanently (no TTL)."""
    r = await get_redis()
    if r is None:
        return
    await r.set(f"geocode:{place_name}", json.dumps({"lat": lat, "lng": lng}))


async def set_cached_geocode_miss(place_name: str) -> None:
    """Cache a geocode miss permanently so we don't re-query Nominatim."""
    r = await get_redis()
    if r is None:
        return
    await r.set(f"geocode:{place_name}", json.dumps(None))
