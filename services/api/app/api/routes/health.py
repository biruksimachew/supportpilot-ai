from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.core.database import check_database_readiness


router = APIRouter(
    prefix="/health",
    tags=["health"],
)


@router.get("/live")
def liveness() -> dict[str, str]:
    """
    Confirm that the SupportPilot API process is alive.
    """
    return {
        "status": "ok",
        "service": "supportpilot-api",
        "environment": settings.environment,
    }


@router.get("/ready")
def readiness():
    """
    Confirm that required application dependencies are available.
    """
    try:
        dependencies = check_database_readiness()
    except Exception:
        return JSONResponse(
            status_code=503,
            content={
                "status": "not_ready",
                "service": "supportpilot-api",
                "dependencies": {
                    "database": False,
                    "pgvector": False,
                },
            },
        )

    ready = all(dependencies.values())

    return JSONResponse(
        status_code=200 if ready else 503,
        content={
            "status": "ready" if ready else "not_ready",
            "service": "supportpilot-api",
            "dependencies": dependencies,
        },
    )