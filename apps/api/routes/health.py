from fastapi import APIRouter

from apps.api.schemas import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok")
