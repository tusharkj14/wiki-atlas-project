from fastapi import APIRouter, HTTPException

from apps.api.schemas import (
    ExtractRequest,
    ExtractResponse,
    GeoTagResponse,
    ScrapeAndExtractRequest,
    ScrapeAndExtractResponse,
)
from lib.types.models import GeoTag
from services.nlp.geotagger import extract_locations
from services.scraper.wikipedia import scrape, validate_wikipedia_url

router = APIRouter()


def _tags_to_response(tags: list[GeoTag]) -> list[GeoTagResponse]:
    return [
        GeoTagResponse(
            place_name=t.place_name,
            place_type=t.place_type.value,
            relationship=t.relationship.value,
            reason=t.reason,
            source_sentence=t.source_sentence,
        )
        for t in tags
    ]


@router.post("/extract", response_model=ExtractResponse)
async def extract_from_text(req: ExtractRequest):
    """Extract geographic locations from raw text using an LLM."""
    try:
        tags = await extract_locations(req.text, req.title)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    locations = _tags_to_response(tags)
    return ExtractResponse(
        title=req.title,
        locations=locations,
        location_count=len(locations),
    )


@router.post("/scrape-and-extract", response_model=ScrapeAndExtractResponse)
async def scrape_and_extract(req: ScrapeAndExtractRequest):
    """Scrape a Wikipedia article and extract locations in one call."""
    try:
        validate_wikipedia_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        article = await scrape(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch article: {e}")

    try:
        tags = await extract_locations(article.full_text, article.title)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=f"LLM extraction failed: {e}")

    locations = _tags_to_response(tags)
    return ScrapeAndExtractResponse(
        url=article.url,
        url_hash=article.url_hash,
        title=article.title,
        locations=locations,
        location_count=len(locations),
        paragraph_count=len(article.paragraphs),
        char_count=len(article.full_text),
    )
