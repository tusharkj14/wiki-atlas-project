"""
Geocoder service — resolves place names to lat/lng via Nominatim (OpenStreetMap).

Respects Nominatim's 1 request/second rate limit.
"""

import asyncio
import logging
from typing import Optional

import httpx

from lib.types.models import GeoTag, GeocodedTag

logger = logging.getLogger(__name__)

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "Mozilla/5.0 (compatible; WikiAtlas/1.0; +https://github.com/wikiatlas)"

# ISO 3166-1 alpha-2 country code lookup for Nominatim's countrycodes param.
# Covers common countries; unknown names fall back to unbiased search.
_COUNTRY_CODES: dict[str, str] = {
    "india": "in", "china": "cn", "japan": "jp", "turkey": "tr",
    "france": "fr", "germany": "de", "italy": "it", "spain": "es",
    "united kingdom": "gb", "uk": "gb", "england": "gb", "scotland": "gb",
    "wales": "gb", "russia": "ru", "united states": "us", "usa": "us",
    "brazil": "br", "mexico": "mx", "canada": "ca", "australia": "au",
    "pakistan": "pk", "iran": "ir", "iraq": "iq", "egypt": "eg",
    "south africa": "za", "nigeria": "ng", "kenya": "ke",
    "indonesia": "id", "thailand": "th", "vietnam": "vn",
    "south korea": "kr", "north korea": "kp", "saudi arabia": "sa",
    "afghanistan": "af", "uzbekistan": "uz", "bangladesh": "bd",
    "nepal": "np", "sri lanka": "lk", "myanmar": "mm",
    "greece": "gr", "poland": "pl", "ukraine": "ua", "portugal": "pt",
    "netherlands": "nl", "belgium": "be", "sweden": "se", "norway": "no",
    "denmark": "dk", "finland": "fi", "austria": "at", "switzerland": "ch",
    "czech republic": "cz", "hungary": "hu", "romania": "ro",
    "argentina": "ar", "chile": "cl", "colombia": "co", "peru": "pe",
    "ethiopia": "et", "tanzania": "tz", "morocco": "ma", "algeria": "dz",
    "malaysia": "my", "philippines": "ph", "singapore": "sg",
    "new zealand": "nz", "ireland": "ie", "israel": "il", "syria": "sy",
    "jordan": "jo", "lebanon": "lb", "mongolia": "mn",
}

# In-memory cache for the lifetime of the process — avoids re-geocoding
# the same place name across multiple requests. Will be replaced by Redis.
_geocode_cache: dict[str, Optional[tuple[float, float]]] = {}


def _country_to_code(country: str) -> Optional[str]:
    """Map a country name to an ISO 3166-1 alpha-2 code."""
    if not country:
        return None
    return _COUNTRY_CODES.get(country.strip().lower())


async def geocode_place(place_name: str, country: str = "") -> Optional[tuple[float, float]]:
    """
    Resolve a single place name to (lat, lng) via Nominatim.

    Checks Redis cache first, then in-memory cache, then Nominatim.
    Uses country hint for disambiguation when available.
    Returns None if the place cannot be geocoded.
    """
    cache_key = f"{place_name}||{country}" if country else place_name

    # 1. In-memory cache (process-local)
    if cache_key in _geocode_cache:
        return _geocode_cache[cache_key]

    # 2. Redis cache (persistent across restarts)
    from db.redis.cache import get_cached_geocode, set_cached_geocode, set_cached_geocode_miss
    redis_result = await get_cached_geocode(cache_key)
    if redis_result is not None:
        _geocode_cache[cache_key] = redis_result
        return redis_result

    # 3. Nominatim lookup
    params: dict[str, str | int] = {
        "q": place_name,
        "format": "jsonv2",
        "limit": 1,
        "email": "wikiatlas-project@example.com",
    }

    # Bias results to the expected country
    country_code = _country_to_code(country)
    if country_code:
        params["countrycodes"] = country_code

    async with httpx.AsyncClient(
        headers={"User-Agent": USER_AGENT},
        timeout=10.0,
    ) as client:
        resp = await client.get(NOMINATIM_URL, params=params)
        resp.raise_for_status()
        results = resp.json()

    if not results:
        logger.debug("No geocode result for: %s (country=%s)", place_name, country)
        _geocode_cache[cache_key] = None
        await set_cached_geocode_miss(cache_key)
        return None

    lat = float(results[0]["lat"])
    lng = float(results[0]["lon"])
    _geocode_cache[cache_key] = (lat, lng)
    await set_cached_geocode(cache_key, lat, lng)
    return (lat, lng)


async def geocode_tags(tags: list[GeoTag]) -> list[GeocodedTag]:
    """
    Geocode a list of GeoTags concurrently.

    Cache hits and duplicates resolve instantly. Only true Nominatim lookups
    are rate-limited to 1 req/sec via staggered launch times, but all HTTP
    requests overlap — so total wall time ≈ max(n_uncached_seconds, network_latency)
    instead of n * (1 + latency).
    """
    # 1. De-duplicate: group tags by cache key, only geocode each unique place once
    from collections import OrderedDict

    unique: OrderedDict[str, tuple[str, str]] = OrderedDict()  # cache_key → (place_name, country)
    for tag in tags:
        cache_key = f"{tag.place_name}||{tag.country}" if tag.country else tag.place_name
        if cache_key not in unique:
            unique[cache_key] = (tag.place_name, tag.country)

    # 2. Separate cached hits from places that need Nominatim calls
    from db.redis.cache import get_cached_geocode
    cached_results: dict[str, Optional[tuple[float, float]]] = {}
    uncached: list[tuple[str, str, str]] = []  # (cache_key, place_name, country)

    for cache_key, (place_name, country) in unique.items():
        # Check in-memory cache
        if cache_key in _geocode_cache:
            cached_results[cache_key] = _geocode_cache[cache_key]
            continue
        # Check Redis cache
        redis_result = await get_cached_geocode(cache_key)
        if redis_result is not None:
            _geocode_cache[cache_key] = redis_result
            cached_results[cache_key] = redis_result
            continue
        uncached.append((cache_key, place_name, country))

    logger.info(
        "Geocoding: %d unique places (%d cached, %d need Nominatim)",
        len(unique), len(cached_results), len(uncached),
    )

    # 3. Fire Nominatim requests concurrently with staggered 1-second starts
    async def _staggered_geocode(
        index: int, cache_key: str, place_name: str, country: str,
    ) -> tuple[str, Optional[tuple[float, float]]]:
        """Wait index seconds, then fire the request."""
        await asyncio.sleep(index)  # stagger: 0s, 1s, 2s, ...
        coords = await geocode_place(place_name, country)
        return cache_key, coords

    if uncached:
        tasks = [
            _staggered_geocode(i, ck, pn, co)
            for i, (ck, pn, co) in enumerate(uncached)
        ]
        nominatim_results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in nominatim_results:
            if isinstance(result, Exception):
                logger.warning("Geocode failed: %s", result)
                continue
            ck, coords = result
            cached_results[ck] = coords

    # 4. Build final results in original tag order
    results: list[GeocodedTag] = []
    for tag in tags:
        cache_key = f"{tag.place_name}||{tag.country}" if tag.country else tag.place_name
        coords = cached_results.get(cache_key)
        results.append(
            GeocodedTag(
                place_name=tag.place_name,
                place_type=tag.place_type,
                relationship=tag.relationship,
                reason=tag.reason,
                source_sentence=tag.source_sentence,
                country=tag.country,
                lat=coords[0] if coords else None,
                lng=coords[1] if coords else None,
                geocoder="nominatim" if coords else None,
            )
        )

    geocoded_count = sum(1 for r in results if r.lat is not None)
    logger.info("Geocoded %d/%d places", geocoded_count, len(results))
    return results
