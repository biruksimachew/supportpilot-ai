from datetime import datetime
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


class KnowledgeRetrievalRequest(
    BaseModel
):
    question: str = Field(
        min_length=3,
        max_length=4000,
    )

    top_k: int = Field(
        default=5,
        ge=1,
        le=10,
    )

    min_similarity: float = Field(
        default=0.0,
        ge=-1.0,
        le=1.0,
    )


class KnowledgeRetrievalResult(
    BaseModel
):
    chunk_id: UUID
    source_id: UUID

    title: str
    type: str
    version: str

    section: str | None
    content: str

    similarity: float

    effective_at: datetime

    source_metadata: dict
    chunk_metadata: dict


class KnowledgeRetrievalResponse(
    BaseModel
):
    question: str

    provider: str
    model: str
    dimensions: int

    top_k: int
    min_similarity: float

    results: list[
        KnowledgeRetrievalResult
    ]