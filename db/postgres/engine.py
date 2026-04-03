"""
Async SQLAlchemy engine and session factory for PostgreSQL.
"""

import os

from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "")

engine = create_async_engine(DATABASE_URL, echo=False) if DATABASE_URL else None

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
