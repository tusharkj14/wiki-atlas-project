"""
Wikipedia main page section endpoints.

GET /main-page/{section} — scrape, geotag, and geocode a section from
Wikipedia's main page. Sections: in_the_news, on_this_day, did_you_know.
"""

import logging
from enum import Enum

from fastapi import APIRouter, HTTPException

from services.pipeline.process_main_page import process_main_page_section

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/main-page", tags=["main-page"])


class Section(str, Enum):
    in_the_news = "in_the_news"
    on_this_day = "on_this_day"
    did_you_know = "did_you_know"


@router.get("/{section}")
async def get_main_page_section(section: Section):
    """
    Scrape a section from Wikipedia's main page, run it through the
    geotagger + geocoder pipeline, and return GeoJSON + item metadata.
    """
    try:
        result = await process_main_page_section(section.value)
    except Exception as e:
        logger.exception("Main page pipeline failed for section: %s", section.value)
        raise HTTPException(status_code=502, detail=f"Pipeline failed: {e}")

    return {
        "section": result.section,
        "items": result.items,
        "geojson": result.geojson,
        "total_items": result.total_items,
        "total_geocoded": result.total_geocoded,
    }
