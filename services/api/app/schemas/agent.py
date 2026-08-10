from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class AgentQueueItem(BaseModel):
    id: UUID
    reference: str

    channel: str
    status: str
    priority: str

    intent: str | None
    confidence_band: str | None

    customer_name: str | None
    customer_email: str | None

    assignee_name: str | None

    created_at: datetime
    updated_at: datetime

    message_count: int

    last_message_body: str | None
    last_message_at: datetime | None


class AgentQueueResponse(BaseModel):
    items: list[AgentQueueItem]
    total: int
    limit: int
    offset: int


class AgentTicketMessage(BaseModel):
    id: UUID
    direction: str
    sender_type: str

    body: str
    is_internal: bool

    sent_at: datetime
    received_at: datetime


class AgentOrderSummary(BaseModel):
    external_order_id: str
    status: str
    fulfillment_summary: dict
    total_summary: dict
    retrieved_at: datetime


class AgentAuditEvent(BaseModel):
    id: UUID
    actor_type: str
    event_type: str
    entity_type: str
    entity_id: str
    metadata: dict
    created_at: datetime


class AgentTicketDetail(BaseModel):
    id: UUID
    reference: str

    channel: str
    status: str
    priority: str

    intent: str | None
    confidence_band: str | None

    restricted_action: bool
    escalation_reason: str | None
    resolution_code: str | None

    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None

    customer_id: UUID | None
    customer_name: str | None
    customer_email: str | None

    assignee_id: UUID | None
    assignee_name: str | None

    messages: list[AgentTicketMessage]
    orders: list[AgentOrderSummary]
    audit_events: list[AgentAuditEvent]