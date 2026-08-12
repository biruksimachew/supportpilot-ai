from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.grounded_generation import (
    GroundedAnswerResponse,
)


ConfidenceBand = Literal[
    "HIGH",
    "MEDIUM",
    "LOW",
]


AIDecision = Literal[
    "AUTO_RESPOND",
    "REVIEW_REQUIRED",
    "REQUEST_CLARIFICATION",
    "FAILED",
]


class TicketAIDraftResponse(BaseModel):
    ai_run_id: UUID

    ticket_id: UUID
    message_id: UUID

    confidence: float
    confidence_band: ConfidenceBand

    decision: AIDecision
    decision_reasons: list[str]

    evidence_count: int
    contradiction_detected: bool

    generation_attempted: bool

    answer: GroundedAnswerResponse