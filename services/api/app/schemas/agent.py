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


class AgentAIRunSummary(BaseModel):
    id: UUID

    message_id: UUID | None

    source_message_body: str | None

    provider: str
    model: str

    prompt_version: str

    intent: str | None

    confidence: float | None
    confidence_band: str | None

    decision: str

    decision_reasons: list[str]

    safe_draft_ready: bool

    auto_response_eligible: bool

    latency_ms: int | None

    error_code: str | None

    created_at: datetime


class AgentRetrievalEvidence(BaseModel):
    chunk_id: UUID

    rank: int
    score: float | None

    section: str | None
    content: str

    source_id: UUID

    source_title: str
    source_type: str

    source_version: str

    source_status: str

    source_effective_at: datetime | None


class AgentToolCall(BaseModel):
    id: UUID

    tool_name: str

    safe_request_summary: str | None

    result_summary: str | None

    status: str

    latency_ms: int | None

    created_at: datetime

class AgentDraftSnapshot(BaseModel):
    action_id: UUID

    ai_run_id: UUID

    source_message_id: UUID | None

    answer_status: str | None

    original_body: str

    decision: str

    decision_reasons: list[str]

    safe_draft_ready: bool

    created_at: datetime
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

    identity_verification_status: str

    identity_verification_method: str | None  

    identity_verified_at:datetime | None

    identity_verified_order_number: str | None

    identity_verification_attempts: int

    messages: list[AgentTicketMessage]

    orders: list[AgentOrderSummary]

    latest_ai_run: AgentAIRunSummary | None

    retrieval_evidence: list[AgentRetrievalEvidence]

    tool_calls: list[AgentToolCall]

    audit_events: list[AgentAuditEvent]
    latest_draft: AgentDraftSnapshot | None