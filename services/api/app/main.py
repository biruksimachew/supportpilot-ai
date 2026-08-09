from fastapi import FastAPI

from app.api.routes.chat import (
    router as chat_router,
)
from app.api.routes.health import (
    router as health_router,
)
from app.api.routes.intake import (
    router as intake_router,
)
from app.core.config import settings


app = FastAPI(
    title=settings.app_name,
    version="0.2.1",
    description=(
        "SupportPilot AI support core API."
    ),
)


app.include_router(health_router)
app.include_router(intake_router)
app.include_router(chat_router)


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "supportpilot-api",
        "status": "running",
    }