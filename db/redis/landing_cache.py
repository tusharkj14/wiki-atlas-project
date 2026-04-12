"""
Redis cache for landing page (main page sections).

Uses the main Redis instance with a "landing:" key prefix to isolate
landing page data from the main article cache. TTL is 1 day (main page updates daily).
"""

import json
import logging
from typing import Any, Optional

from dotenv import load_dotenv

from db.redis.cache import _get, _set, get_redis

load_dotenv()

logger = logging.getLogger(__name__)

LANDING_TTL = 60 * 60 * 24  # 1 day


def get_landing_redis():
    """Get the main Redis instance (shared with article cache)."""
    return get_redis()


async def close_landing_redis():
    """No-op: landing cache shares the main Redis connection, which is closed separately."""
    pass


def _key(section: str) -> str:
    """Build the landing page cache key."""
    return f"landing:mainpage:{section}"


async def get_landing_cached(section: str) -> Optional[dict]:
    """Get cached main page section result."""
    r = get_landing_redis()
    if r is None:
        return None

    try:
        raw = await _get(r, _key(section))
        if raw:
            return json.loads(raw)
    except Exception as e:
        logger.warning("Landing cache read failed: %s", e)
    return None


async def set_landing_cached(section: str, value: Any) -> None:
    """Cache a main page section result with 1-day TTL."""
    r = get_landing_redis()
    if r is None:
        return

    try:
        serialized = json.dumps(value)
        await _set(r, _key(section), serialized, ex=LANDING_TTL)
        logger.info("Landing cache: stored section '%s' (TTL %ds)", section, LANDING_TTL)
    except Exception as e:
        logger.warning("Landing cache write failed: %s", e)
