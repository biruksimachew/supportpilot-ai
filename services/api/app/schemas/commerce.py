from datetime import (
    date,
    datetime,
)

from uuid import UUID

from pydantic import (
    BaseModel,
    Field,
)


class CommerceOrderItem(
    BaseModel
):
    sku: str
    name: str

    quantity: int = Field(
        ge=1,
    )

    status: str | None = None


class CommerceOrder(
    BaseModel
):
    order_number: str
    customer_id: str

    status: str

    items: list[
        CommerceOrderItem
    ]

    tracking_number: str | None = None

    delivered_at: date | None = None

    total: float = Field(
        ge=0,
    )

    currency: str


class CommerceOrderLookupRequest(
    BaseModel
):
    customer_id: UUID

    order_number: str = Field(
        min_length=3,
        max_length=100,
    )

    ai_run_id: UUID | None = None


class CommerceOrderLookupResponse(
    BaseModel
):
    customer_id: UUID

    order: CommerceOrder

    cached_at: datetime

    tool_call_id: UUID | None = None