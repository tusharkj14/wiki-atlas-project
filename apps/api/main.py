"""
FastAPI sidecar — app factory.

Registers middleware, includes all route modules, and manages
database/cache lifecycle (startup + shutdown).
"""

import logging
from contextlib import asynccontextmanager

import os
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from apps.api.routes import health, scraper, nlp, pipeline, share

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # ── Startup ─────────────────────────────────────────────────────
    from db.postgres.engine import init_db
    from db.redis.cache import get_redis

    try:
        await init_db()
        logger.info("PostgreSQL initialised")
    except Exception as e:
        logger.warning("PostgreSQL not available: %s", e)

    try:
        r = await get_redis()
        if r:
            await r.ping()
            logger.info("Redis connected")
        else:
            logger.info("Redis not configured (REDIS_URL not set)")
    except Exception as e:
        logger.warning("Redis not available: %s", e)

    yield

    # ── Shutdown ────────────────────────────────────────────────────
    from db.postgres.engine import close_db
    from db.redis.cache import close_redis

    await close_redis()
    await close_db()
    logger.info("Connections closed")


def create_app() -> FastAPI:
    app = FastAPI(title="WikiAtlas API", version="0.1.0", lifespan=lifespan)

    
    origins = [
        "http://localhost:3000",
        "https://wikiatlas.vercel.app",
    ]
    extra = os.getenv("CORS_ORIGIN", "")
    if extra:
        origins.append(extra)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(health.router)
    app.include_router(scraper.router)
    app.include_router(nlp.router)
    app.include_router(pipeline.router)
    app.include_router(share.router)

    return app


app = create_app()
