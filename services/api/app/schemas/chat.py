from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


class ChatSessionResponse(BaseModel):
    session_id: UUID
    session_token: str
    expires_at: datetime


class ChatMessageRequest(BaseModel):
    client_message_id: UUID

    body: str = Field(
        min_length=1,
        max_length=50000,
    )

    customer_hint: str | None = Field(
        default=None,
        max_length=512,
    )

    @field_validator("body")
    @classmethod
    def normalize_body(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError(
                "body must not be blank"
            )

        return value

    @field_validator(
        "customer_hint",
        mode="before",
    )
    @classmethod
    def normalize_customer_hint(
        cls,
        value,
    ):
        if isinstance(value, str):
            value = value.strip()

            if not value:
                return None

        return value


class ChatMessageResponse(BaseModel):
    ticket_id: UUID
    ticket_reference: str
    ticket_status: str
    message_id: UUID

    duplicate: bool
    created_ticket: bool


class ChatHistoryMessage(BaseModel):
    id: UUID
    direction: str
    sender_type: str
    body: str
    sent_at: datetime


class ChatHistoryResponse(BaseModel):
    session_id: UUID

    ticket_reference: str | None
    ticket_status: str | None

    messages: list[ChatHistoryMessage]