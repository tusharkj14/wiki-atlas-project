"""
Database queries for articles and geotags.
"""

import secrets
import logging
from typing import Optional

from geoalchemy2.elements import WKTElement
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from db.postgres.engine import async_session
from db.postgres.models import Article, GeoTagRow
from lib.types.models import GeocodedTag, ScrapedArticle

logger = logging.getLogger(__name__)


def _generate_slug() -> str:
    return secrets.token_urlsafe(6)[:8]


async def get_article_by_hash(url_hash: str) -> Optional[Article]:
    """Look up an article by its URL hash, eagerly loading geotags."""
    if async_session is None:
        return None
    async with async_session() as session:
        stmt = (
            select(Article)
            .options(selectinload(Article.geotags))
            .where(Article.url_hash == url_hash)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()


async def save_article(
    article: ScrapedArticle,
    geocoded_tags: list[GeocodedTag],
) -> Article:
    """Persist a scraped article and its geocoded tags. Returns the Article row."""
    if async_session is None:
        raise RuntimeError("DATABASE_URL not configured")

    async with async_session() as session:
        async with session.begin():
            row = Article(
                url=article.url,
                url_hash=article.url_hash,
                title=article.title,
                share_slug=_generate_slug(),
            )
            session.add(row)
            await session.flush()  # get row.id

            for tag in geocoded_tags:
                geog = None
                if tag.lat is not None and tag.lng is not None:
                    geog = WKTElement(f"POINT({tag.lng} {tag.lat})", srid=4326)

                session.add(GeoTagRow(
                    article_id=row.id,
                    place_name=tag.place_name,
                    place_type=tag.place_type.value,
                    relationship_=tag.relationship.value,
                    lat=tag.lat,
                    lng=tag.lng,
                    reason=tag.reason,
                    source_sentence=tag.source_sentence,
                    geocoder=tag.geocoder,
                    geog=geog,
                ))

        logger.info("Saved article '%s' with %d geotags (slug=%s)", article.title, len(geocoded_tags), row.share_slug)
        return row


async def get_article_by_slug(slug: str) -> Optional[Article]:
    """Look up an article by its share slug."""
    if async_session is None:
        return None
    async with async_session() as session:
        stmt = (
            select(Article)
            .options(selectinload(Article.geotags))
            .where(Article.share_slug == slug)
        )
        result = await session.execute(stmt)
        return result.scalar_one_or_none()
