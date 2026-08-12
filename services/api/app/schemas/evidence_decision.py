from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.schemas.commerce import (
    CommerceOrder,
)

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

    # ------------------------------------------------------
    # M4 unified decision context.
    # ------------------------------------------------------

    intent: str | None = None

    commerce_required:bool = False

    order_number: str | None = None

    safe_draft_ready: bool = False

    commerce_order: CommerceOrder | None = None

    commerce_tool_call_id: UUID | None = None