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

from app.api.routes.agent import (
    router as agent_router,
)
from app.api.routes.email_intake import (
    router as email_intake_router,
)
from app.api.routes.knowledge import (
    router as knowledge_router,
)
from app.api.routes.knowledge_index import (
    router as knowledge_index_router,
)
from app.api.routes.knowledge_retrieval import (
    router as knowledge_retrieval_router,
)
from app.api.routes.grounded_answer import (
    router as grounded_answer_router,
)
from app.api.routes.identity_verification import (
    router as identity_verification_router,
)
app = FastAPI(
    title=settings.app_name,
    version="0.4.2",
    description=(
        "SupportPilot AI support core API."
    ),
)
from app.api.routes.support_ai import (
    router as support_ai_router,
)
from app.api.routes.commerce import (
    router as commerce_router,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        settings.web_origin,
    ],
    allow_methods=[
        "GET",
        "POST",
        "PUT",
        "OPTIONS",
    ],
    allow_headers=[
        "Authorization",
        "Content-Type",
        "X-Chat-Session-Token",
    ],
)


app.include_router(health_router)
app.include_router(intake_router)
app.include_router(chat_router)
app.include_router(agent_router)
app.include_router(email_intake_router)
app.include_router(knowledge_router)
app.include_router(knowledge_index_router)
app.include_router(knowledge_retrieval_router)
app.include_router(grounded_answer_router)
app.include_router(support_ai_router)
app.include_router(commerce_router)
app.include_router(identity_verification_router)

@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {
        "service": "supportpilot-api",
        "status": "running",
    }