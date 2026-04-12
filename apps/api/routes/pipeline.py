import json
import logging

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse

from apps.api.schemas import ProcessRequest, ProcessResponse
from services.scraper.wikipedia import validate_wikipedia_url
from services.pipeline.process_page import process_page
from services.pipeline.stream_page import stream_process_page

logger = logging.getLogger(__name__)
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
        logger.exception("Pipeline runtime error for %s", req.url)
        raise HTTPException(status_code=502, detail=str(e))
    except Exception as e:
        logger.exception("Pipeline failed for %s", req.url)
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


@router.get("/process/stream")
async def stream_process_article(url: str = Query(...)):
    """
    SSE endpoint: streams pins as they are geocoded.

    Events:
      event: meta    — {title, url, url_hash, total_extracted}
      event: pin     — a GeoJSON Feature
      event: done    — {total_geocoded, share_slug, cache_hit}
      event: error   — {message}
    """
    try:
        validate_wikipedia_url(url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    async def event_generator():
        try:
            async for msg in stream_process_page(url):
                event = msg["event"]
                data = json.dumps(msg["data"])
                yield f"event: {event}\ndata: {data}\n\n"
        except Exception as e:
            logger.exception("Stream pipeline failed for %s", url)
            error_data = json.dumps({"message": str(e)})
            yield f"event: error\ndata: {error_data}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
