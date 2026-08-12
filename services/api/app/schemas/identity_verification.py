from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import (
    BaseModel,
    EmailStr,
    Field,
)


VerificationStatus = Literal[
    "VERIFIED",
    "FAILED",
]


class CustomerVerificationRequest(
    BaseModel
):
    email: EmailStr

    postcode: str = Field(
        min_length=2,
        max_length=32,
    )

    order_number: str = Field(
        min_length=3,
        max_length=100,
    )


class CustomerVerificationResponse(
    BaseModel
):
    ticket_id: UUID

    verification_status:VerificationStatus

    verified: bool

    customer_id:UUID | None = None

    verified_order_number: str | None = None

    verification_method: str | None = None

    attempts: int

    verified_at: datetime | None = None