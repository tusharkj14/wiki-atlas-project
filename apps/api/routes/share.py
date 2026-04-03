from fastapi import APIRouter, HTTPException

from apps.api.schemas import ProcessResponse
from db.postgres.queries import get_article_by_slug

router = APIRouter()


@router.get("/article/{slug}", response_model=ProcessResponse)
async def get_article(slug: str):
    """Retrieve a processed article by its share slug."""
    article = await get_article_by_slug(slug)
    if article is None:
        raise HTTPException(status_code=404, detail="Article not found")

    features = []
    for tag in article.geotags:
        if tag.lat is None or tag.lng is None:
            continue
        features.append({
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [tag.lng, tag.lat],
            },
            "properties": {
                "place_name": tag.place_name,
                "place_type": tag.place_type,
                "relationship": tag.relationship_,
                "reason": tag.reason,
                "source_sentence": tag.source_sentence,
                "geocoder": tag.geocoder,
            },
        })

    geojson = {"type": "FeatureCollection", "features": features}

    return ProcessResponse(
        url=article.url,
        url_hash=article.url_hash,
        title=article.title,
        geojson=geojson,
        total_extracted=len(article.geotags),
        total_geocoded=len(features),
        share_slug=article.share_slug,
        cache_hit=True,
    )
