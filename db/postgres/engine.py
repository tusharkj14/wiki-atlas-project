"""
Async SQLAlchemy engine and session factory for PostgreSQL.
"""

import os
import ssl as stdlib_ssl
from urllib.parse import parse_qs, urlencode, urlparse, urlunparse

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")


def _prepare_engine_args(url: str) -> tuple[str, dict]:
    """Strip sslmode from the URL and return (clean_url, connect_args) for asyncpg."""
    if not url:
        return url, {}

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    sslmode = params.pop("sslmode", [None])

    clean_query = urlencode({k: v[0] for k, v in params.items()})
    clean_url = urlunparse(parsed._replace(query=clean_query))

    connect_args: dict = {}
    if sslmode and sslmode[0] in ("require", "verify-ca", "verify-full"):
        ssl_ctx = stdlib_ssl.create_default_context()
        ssl_ctx.check_hostname = False
        ssl_ctx.verify_mode = stdlib_ssl.CERT_NONE
        connect_args["ssl"] = ssl_ctx

    return clean_url, connect_args


_clean_url, _connect_args = _prepare_engine_args(DATABASE_URL)

engine = (
    create_async_engine(_clean_url, echo=False, connect_args=_connect_args)
    if _clean_url
    else None
)

async_session = (
    async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    if engine
    else None
)


async def init_db():
    """Create all tables if they don't exist."""
    if engine is None:
        return
    from db.postgres.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db():
    """Dispose of the engine connection pool."""
    if engine is not None:
        await engine.dispose()
