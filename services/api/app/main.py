from fastapi import FastAPI

from app.api.routes.health import router as health_router
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="SupportPilot AI support core API.",
)


app.include_router(health_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "supportpilot-api",
        "status": "running",
    }