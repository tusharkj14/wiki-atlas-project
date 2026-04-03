"""
Request and response schemas for the API layer.
"""

from pydantic import BaseModel


# ── Requests ─────────────────────────────────────────────────────────

class ScrapeRequest(BaseModel):
    url: str


class ExtractRequest(BaseModel):
    text: str
    title: str = "Unknown"


class ScrapeAndExtractRequest(BaseModel):
    url: str


# ── Responses ────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str


class ScrapeResponse(BaseModel):
    url: str
    url_hash: str
    title: str
    paragraphs: list[str]
    infobox: dict[str, str]
    captions: list[str]
    full_text: str
    paragraph_count: int
    char_count: int


class PreviewResponse(BaseModel):
    url: str
    title: str
    preview_paragraphs: list[str]
    total_paragraphs: int


class GeoTagResponse(BaseModel):
    place_name: str
    place_type: str
    relationship: str
    reason: str
    source_sentence: str


class ExtractResponse(BaseModel):
    title: str
    locations: list[GeoTagResponse]
    location_count: int


class ScrapeAndExtractResponse(BaseModel):
    url: str
    url_hash: str
    title: str
    locations: list[GeoTagResponse]
    location_count: int
    paragraph_count: int
    char_count: int


# ── Geocode ──────────────────────────────────────────────────────────

class GeocodedTagResponse(BaseModel):
    place_name: str
    place_type: str
    relationship: str
    reason: str
    source_sentence: str
    lat: float | None = None
    lng: float | None = None
    geocoder: str | None = None


# ── Pipeline (full process) ──────────────────────────────────────────

class ProcessRequest(BaseModel):
    url: str


class GeoJSONProperties(BaseModel):
    place_name: str
    place_type: str
    relationship: str
    reason: str
    source_sentence: str
    geocoder: str | None = None


class GeoJSONGeometry(BaseModel):
    type: str = "Point"
    coordinates: list[float]


class GeoJSONFeature(BaseModel):
    type: str = "Feature"
    geometry: GeoJSONGeometry
    properties: GeoJSONProperties


class ProcessResponse(BaseModel):
    url: str
    url_hash: str
    title: str
    geojson: dict
    total_extracted: int
    total_geocoded: int
    share_slug: str | None = None
    cache_hit: bool = False
