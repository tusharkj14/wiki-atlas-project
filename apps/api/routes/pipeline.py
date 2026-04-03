from fastapi import APIRouter, HTTPException

from apps.api.schemas import ProcessRequest, ProcessResponse
from services.scraper.wikipedia import validate_wikipedia_url
from services.pipeline.process_page import process_page

router = APIRouter()


@router.post("/process", response_model=ProcessResponse)
async def process_article(req: ProcessRequest):
    """Full pipeline: scrape → extract locations → geocode → return GeoJSON."""
    try:
        validate_wikipedia_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        result = await process_page(req.url)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")

    return ProcessResponse(
        url=result.article.url,
        url_hash=result.article.url_hash,
        title=result.article.title,
        geojson=result.geojson,
        total_extracted=result.total_extracted,
        total_geocoded=result.total_geocoded,
        share_slug=result.share_slug,
        cache_hit=result.cache_hit,
    )
