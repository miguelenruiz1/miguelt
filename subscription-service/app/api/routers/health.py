"""Health check endpoints."""
from fastapi import APIRouter
from fastapi.responses import ORJSONResponse

router = APIRouter(tags=["health"])


@router.get("/health")
async def liveness():
    return ORJSONResponse({"status": "ok"})


@router.get("/ready")
async def readiness():
    return ORJSONResponse({"status": "ready"})
