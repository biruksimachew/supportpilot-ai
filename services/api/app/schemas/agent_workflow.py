from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
    field_validator,
)


TicketPriority = Literal[
    "P1",
    "P2",
    "P3",
    "P4",
]


AgentResolutionCode = Literal[
    "AGENT_RESOLVED",
    "CUSTOMER_INFO_REQUIRED",
    "POLICY_EXCEPTION",
    "ORDER_ACTION_REQUIRED",
    "TECHNICAL_FAILURE",
    "DUPLICATE",
    "SPAM",
]


class InternalNoteRequest(BaseModel):
    body: str = Field(
        min_length=1,
        max_length=4000,
    )

    @field_validator("body")
    @classmethod
    def validate_body(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Internal note cannot be empty."
            )

        return normalized


class EscalateTicketRequest(BaseModel):
    reason: str = Field(
        min_length=1,
        max_length=500,
    )

    priority: TicketPriority | None = None

    @field_validator("reason")
    @classmethod
    def validate_reason(
        cls,
        value: str,
    ) -> str:
        normalized = value.strip()

        if not normalized:
            raise ValueError(
                "Escalation reason cannot be empty."
            )

        return normalized


class ResolveTicketRequest(BaseModel):
    resolution_code: AgentResolutionCode


class AgentWorkflowResponse(BaseModel):
    ticket_id: UUID

    action_id: UUID

    status: str

    assignee_id:  UUID | None = None

    message_id: UUID | None = None

    escalation_reason: str | None = None

    resolution_code: str | None = None

class AgentSendReplyRequest(BaseModel):
    idempotency_key: UUID

    body: str = Field(
        min_length=1,
        max_length=12000,
    )

    @field_validator("body")
    @classmethod
    def validate_reply_body(
        cls,
        value: str,
    ) -> str:

        normalized = (
            value.strip()
        )

        if not normalized:
            raise ValueError(
                "Reply cannot be empty."
            )

        return normalized


class AgentSendReplyResponse(BaseModel):
    ticket_id: UUID

    delivery_id: UUID

    message_id: UUID | None

    status: str

    ticket_status: str

    channel: str

    edited_from_ai_draft: bool

    idempotent_replay: bool