from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


GroundedAnswerStatus = Literal[
    "ANSWERED",
    "INSUFFICIENT_EVIDENCE",
]


class GroundedModelOutput(BaseModel):
    status: GroundedAnswerStatus

    answer: str = Field(
        min_length=1,
        max_length=8000,
    )

    citation_refs: list[str] = Field(
        description=(
            "Evidence references supporting the answer. "
            "For ANSWERED, include at least one supplied "
            "reference such as K1. For "
            "INSUFFICIENT_EVIDENCE, return an empty list."
        ),
    )


class GroundedCitation(BaseModel):
    ref: str

    chunk_id: UUID
    source_id: UUID

    title: str
    version: str
    section: str | None

    similarity: float


class GroundedAnswerRequest(BaseModel):
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


class GroundedAnswerResponse(BaseModel):
    status: GroundedAnswerStatus

    question: str
    answer: str

    citations: list[
        GroundedCitation
    ]

    generation_provider: str | None
    generation_model: str | None

    retrieval_provider: str
    retrieval_model: str

    input_tokens: int | None = None
    output_tokens: int | None = None
    generation_ms: float | None = None