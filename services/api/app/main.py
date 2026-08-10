from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

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
    version="0.2.2",
    description=(
        "SupportPilot AI support core API."
    ),
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.web_origin,
    ],
    allow_credentials=False,
    allow_methods=[
        "GET",
        "POST",
        "OPTIONS",
    ],
    allow_headers=[
        "Content-Type",
        "X-Chat-Session-Token",
    ],
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