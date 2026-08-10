from datetime import datetime

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)

from app.schemas.intake import (
    AttachmentMetadata,
)


class EmailInboundRequest(BaseModel):
    provider: str = Field(
        default="gmail",
        min_length=1,
        max_length=50,
    )

    external_message_id: str = Field(
        min_length=1,
        max_length=512,
    )

    external_thread_id: str = Field(
        min_length=1,
        max_length=512,
    )

    from_email: EmailStr

    from_name: str | None = Field(
        default=None,
        max_length=255,
    )

    subject: str | None = Field(
        default=None,
        max_length=1000,
    )

    body: str = Field(
        min_length=1,
        max_length=100_000,
    )

    received_at: datetime

    attachments: list[
        AttachmentMetadata
    ] = Field(
        default_factory=list,
    )

    metadata: dict = Field(
        default_factory=dict,
    )


class EmailInboundResponse(BaseModel):
    ticket_id: str
    ticket_reference: str
    ticket_status: str

    message_id: str

    duplicate: bool
    created_ticket: bool