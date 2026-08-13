from datetime import (
    datetime,
)

from uuid import UUID

from pydantic import (
    BaseModel,
)


class DashboardDistributionItem(
    BaseModel
):
    key: str
    count: int


class DashboardQueueSummary(
    BaseModel
):
    open_tickets: int

    review_required: int

    waiting_customer: int

    drafted: int

    new_tickets: int

    urgent_p1_p2: int

    unassigned: int

    restricted_open: int


class DashboardAISummary(
    BaseModel
):
    total_runs: int

    auto_respond: int

    review_required: int

    request_clarification: int

    failed: int

    automation_rate_pct: float | None


class DashboardDeliverySummary(
    BaseModel
):
    total_deliveries: int

    delivered: int

    failed: int

    uncertain: int

    pending: int

    delivery_success_rate_pct: float | None


class DashboardResolutionSummary(
    BaseModel
):
    resolved_tickets: int

    average_resolution_minutes: float | None


class DashboardActivityItem(
    BaseModel
):
    id: UUID

    actor_type: str

    event_type: str

    ticket_id: UUID | None

    ticket_reference: str | None

    created_at: datetime


class AgentDashboardResponse(
    BaseModel
):
    generated_at: datetime

    queue: DashboardQueueSummary

    status_breakdown:list[
            DashboardDistributionItem
        ]

    priority_breakdown:list[
            DashboardDistributionItem
        ]

    channel_breakdown:list[
            DashboardDistributionItem
        ]

    intent_breakdown:list[
            DashboardDistributionItem
        ]

    escalation_breakdown: list[
            DashboardDistributionItem
        ]

    ai: DashboardAISummary

    delivery: DashboardDeliverySummary

    resolution: DashboardResolutionSummary

    recent_activity:list[
            DashboardActivityItem
        ]