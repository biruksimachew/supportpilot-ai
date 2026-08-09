from fastapi import APIRouter

from app.core.config import settings


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
def liveness() -> dict[str, str]:
    """
    Confirm that the SupportPilot API process is alive.

    This endpoint intentionally does not check external dependencies.
    Dependency readiness will be added separately.
    """
    return {
        "status": "ok",
        "service": "supportpilot-api",
        "environment": settings.environment,
    }