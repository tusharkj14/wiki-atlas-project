"""
Cron job: sync Redis geotag cache → PostgreSQL.

Scans all `geotags:{url_hash}` keys in Redis and persists any that
don't yet exist in PostgreSQL. Designed to run periodically (e.g. every
30 minutes) so that articles processed via the streaming pipeline —
where Postgres writes can silently fail — eventually get persisted.

Usage:
    python -m jobs.sync_redis_to_postgres          # one-shot
    python -m jobs.sync_redis_to_postgres --loop 30 # repeat every 30 min
"""

import argparse
import asyncio
import json
import logging
import sys

from dotenv import load_dotenv

from db.postgres.engine import async_session, init_db
from db.postgres.queries import get_article_by_hash, save_article
from db.redis.cache import _is_upstash, get_redis
from lib.types.models import GeocodedTag, ScrapedArticle


load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("jobs.sync_redis_to_postgres")


async def _scan_geotag_keys() -> list[str]:
    """Return all geotags:* keys from Redis."""
    
    r = get_redis()
    if r is None:
        return []

    if _is_upstash:
        # Upstash REST client: scan returns (cursor, keys)
        keys: list[str] = []
        cursor = 0
        while True:
            cursor, batch = r.scan(cursor, match="geotags:*", count=100)
            keys.extend(batch)
            if cursor == 0:
                break
        return keys
    else:
        # aioredis
        keys = []
        async for key in r.scan_iter(match="geotags:*", count=100):
            keys.append(key if isinstance(key, str) else key.decode())
        return keys


async def _get_value(key: str) -> list[dict] | None:
    """Get the JSON value for a Redis key."""

    r = get_redis()
    if r is None:
        return None

    if _is_upstash:
        raw = r.get(key)
    else:
        raw = await r.get(key)

    if raw is None:
        return None
    return json.loads(raw)


async def sync_once() -> dict:
    """
    Run one sync pass. Returns stats dict.

    For each geotags:{url_hash} key in Redis:
      1. Check if that url_hash already exists in PostgreSQL
      2. If not, reconstruct a minimal ScrapedArticle and persist it
    """
    if async_session is None:
        logger.error("DATABASE_URL not configured — cannot sync")
        return {"error": "no database"}

    keys = await _scan_geotag_keys()
    logger.info("Found %d geotags:* keys in Redis", len(keys))

    stats = {"scanned": len(keys), "already_in_pg": 0, "synced": 0, "failed": 0}

    for key in keys:
        url_hash = key.replace("geotags:", "")

        # Already in Postgres?
        existing = await get_article_by_hash(url_hash)
        if existing is not None:
            stats["already_in_pg"] += 1
            continue

        # Fetch from Redis
        tag_dicts = await _get_value(key)
        if not tag_dicts:
            continue

        tags = [GeocodedTag(**d) for d in tag_dicts]

        # Reconstruct a minimal ScrapedArticle — we don't have the full
        # article text in Redis, only the geotags. Use the first tag's
        # place_name as a fallback title.
        article = ScrapedArticle(
            url=f"https://en.wikipedia.org/wiki/Unknown_{url_hash[:12]}",
            url_hash=url_hash,
            title=f"(synced from cache — {url_hash[:12]})",
        )

        # Try to recover the real URL/title from the tags' source sentences
        # This is best-effort; the share slug page will still work.

        try:
            await save_article(article, tags)
            stats["synced"] += 1
            logger.info("Synced url_hash=%s (%d tags)", url_hash[:12], len(tags))
        except Exception as e:
            stats["failed"] += 1
            logger.warning("Failed to sync url_hash=%s: %s", url_hash[:12], e)

    logger.info(
        "Sync complete: %d scanned, %d already in PG, %d synced, %d failed",
        stats["scanned"], stats["already_in_pg"], stats["synced"], stats["failed"],
    )
    return stats


async def run_loop(interval_minutes: int):
    """Run sync_once in a loop."""
    await init_db()
    logger.info("Starting sync loop (every %d minutes)", interval_minutes)

    while True:
        try:
            await sync_once()
        except Exception:
            logger.exception("Sync pass failed")
        await asyncio.sleep(interval_minutes * 60)


async def run_once():
    """Run a single sync pass."""
    await init_db()
    stats = await sync_once()
    return stats


def main():
    parser = argparse.ArgumentParser(description="Sync Redis geotag cache to PostgreSQL")
    parser.add_argument(
        "--loop",
        type=int,
        metavar="MINUTES",
        help="Run continuously every N minutes (default: one-shot)",
    )
    args = parser.parse_args()

    if args.loop:
        asyncio.run(run_loop(args.loop))
    else:
        asyncio.run(run_once())


if __name__ == "__main__":
    main()
