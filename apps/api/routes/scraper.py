from fastapi import APIRouter, HTTPException

from apps.api.schemas import ScrapeRequest, ScrapeResponse, PreviewResponse
from services.scraper.wikipedia import scrape, validate_wikipedia_url

router = APIRouter()


@router.post("/scrape", response_model=ScrapeResponse)
async def scrape_article(req: ScrapeRequest):
    """Scrape a Wikipedia article and return all cleaned text."""
    try:
        validate_wikipedia_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        article = await scrape(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch article: {e}")

    return ScrapeResponse(
        url=article.url,
        url_hash=article.url_hash,
        title=article.title,
        paragraphs=article.paragraphs,
        infobox=article.infobox,
        captions=article.captions,
        full_text=article.full_text,
        paragraph_count=len(article.paragraphs),
        char_count=len(article.full_text),
    )


@router.post("/scrape/preview", response_model=PreviewResponse)
async def scrape_preview(req: ScrapeRequest):
    """Scrape a Wikipedia article and return only the first 3 paragraphs."""
    try:
        validate_wikipedia_url(req.url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        article = await scrape(req.url)
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Failed to fetch article: {e}")

    return PreviewResponse(
        url=article.url,
        title=article.title,
        preview_paragraphs=article.paragraphs[:3],
        total_paragraphs=len(article.paragraphs),
    )
