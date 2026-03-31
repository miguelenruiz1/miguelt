from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def health() -> ORJSONResponse:
    return ORJSONResponse(content={"status": "ok", "service": "media-service"})
