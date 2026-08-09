from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field, field_validator


Channel = Literal["chat", "email"]


class AttachmentMetadata(BaseModel):
    name: str = Field(min_length=1)
    content_type: str | None = None
    size_bytes: int | None = Field(default=None, ge=0)
    external_id: str | None = None


class InboundMessageRequest(BaseModel):
    channel: Channel

    external_message_id: str = Field(
        min_length=1,
        max_length=512,
    )

    external_thread_id: str | None = Field(
        default=None,
        max_length=512,
    )

    customer_hint: str | None = Field(
        default=None,
        max_length=512,
    )

    subject: str | None = Field(
        default=None,
        max_length=1000,
    )

    body: str = Field(
        min_length=1,
        max_length=50000,
    )

    received_at: datetime

    attachments: list[AttachmentMetadata] = Field(
        default_factory=list
    )

    metadata: dict[str, Any] = Field(
        default_factory=dict
    )

    @field_validator(
        "external_message_id",
        "external_thread_id",
        "customer_hint",
        "subject",
        mode="before",
    )
    @classmethod
    def normalize_optional_strings(cls, value):
        if isinstance(value, str):
            value = value.strip()

            if value == "":
                return None

        return value

    @field_validator("body")
    @classmethod
    def body_must_not_be_blank(cls, value: str) -> str:
        value = value.strip()

        if not value:
            raise ValueError("body must not be blank")

        return value

    @field_validator("received_at")
    @classmethod
    def received_at_must_be_timezone_aware(
        cls,
        value: datetime,
    ) -> datetime:
        if value.tzinfo is None:
            raise ValueError(
                "received_at must include a timezone"
            )

        return value


class InboundMessageResponse(BaseModel):
    ticket_id: UUID
    ticket_reference: str

    message_id: UUID

    ticket_status: str

    duplicate: bool
    created_ticket: bool