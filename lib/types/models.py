"""
Domain models shared across services and API layers.
"""

from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel


class PlaceType(str, Enum):
    city = "city"
    country = "country"
    region = "region"
    landmark = "landmark"
    battle_site = "battle_site"
    natural_feature = "natural_feature"
    other = "other"


class Relationship(str, Enum):
    birthplace = "birthplace"
    death_place = "death_place"
    battle_site = "battle_site"
    headquarters = "headquarters"
    founded_in = "founded_in"
    visited = "visited"
    mentioned = "mentioned"
    other = "other"


class GeoTag(BaseModel):
    place_name: str
    place_type: PlaceType
    relationship: Relationship
    reason: str
    source_sentence: str
    country: str = ""
    city: str = ""


class GeocodedTag(BaseModel):
    """GeoTag enriched with coordinates from the geocoder."""
    place_name: str
    place_type: PlaceType
    relationship: Relationship
    reason: str
    source_sentence: str
    country: str = ""
    city: str = ""
    lat: float | None = None
    lng: float | None = None
    geocoder: str | None = None


@dataclass
class ScrapedArticle:
    """Result of scraping a single Wikipedia article."""

    url: str
    url_hash: str
    title: str
    paragraphs: list[str] = field(default_factory=list)
    infobox: dict[str, str] = field(default_factory=dict)
    captions: list[str] = field(default_factory=list)

    @property
    def full_text(self) -> str:
        """All extracted text joined for LLM consumption."""
        parts: list[str] = []

        if self.infobox:
            infobox_lines = [f"{k}: {v}" for k, v in self.infobox.items()]
            parts.append("INFOBOX:\n" + "\n".join(infobox_lines))

        if self.paragraphs:
            parts.append("ARTICLE TEXT:\n" + "\n\n".join(self.paragraphs))

        if self.captions:
            parts.append("IMAGE CAPTIONS:\n" + "\n".join(self.captions))

        return "\n\n".join(parts)
