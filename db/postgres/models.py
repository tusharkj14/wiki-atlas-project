"""
SQLAlchemy ORM models for PostgreSQL/PostGIS.

Tables:
  - articles  : scraped Wikipedia articles
  - geotags   : extracted location mentions with coordinates
"""

import uuid
from datetime import datetime, timezone

from geoalchemy2 import Geography
from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import DeclarativeBase, relationship


class Base(DeclarativeBase):
    pass


class Article(Base):
    __tablename__ = "articles"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    url = Column(Text, unique=True, nullable=False)
    url_hash = Column(String(64), unique=True, nullable=False)
    title = Column(Text, nullable=False)
    scraped_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    share_slug = Column(String(8), unique=True, nullable=True)

    geotags = relationship("GeoTagRow", back_populates="article", cascade="all, delete-orphan")


class GeoTagRow(Base):
    __tablename__ = "geotags"

    id = Column(Uuid, primary_key=True, default=uuid.uuid4)
    article_id = Column(Uuid, ForeignKey("articles.id", ondelete="CASCADE"), nullable=False)
    place_name = Column(Text, nullable=False)
    place_type = Column(
        Enum(
            "city", "country", "region", "landmark",
            "battle_site", "natural_feature", "other",
            name="place_type_enum",
        ),
        nullable=False,
    )
    relationship_ = Column(
        "relationship",
        Enum(
            "birthplace", "death_place", "battle_site", "headquarters",
            "founded_in", "visited", "mentioned", "other",
            name="relationship_enum",
        ),
        nullable=False,
    )
    lat = Column(Float, nullable=True)
    lng = Column(Float, nullable=True)
    reason = Column(Text, nullable=False)
    source_sentence = Column(Text, nullable=False)
    geocoder = Column(String(32), nullable=True)
    created_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # PostGIS geography column — populated from lat/lng for spatial queries
    geog = Column(Geography("POINT", srid=4326), nullable=True)

    article = relationship("Article", back_populates="geotags")
