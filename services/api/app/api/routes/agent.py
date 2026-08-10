from typing import Literal
from uuid import UUID

import psycopg
from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.core.auth import (
    get_current_internal_user,
)
from app.schemas.agent import (
    AgentQueueResponse,
    AgentTicketDetail,
)
from app.schemas.auth import InternalUser
from app.services.agent_queue import (
    get_agent_ticket,
    list_agent_tickets,
)


TicketStatus = Literal[
    "NEW",
    "TRIAGED",
    "DRAFTED",
    "AUTO_RESPONDED",
    "REVIEW_REQUIRED",
    "WAITING_CUSTOMER",
    "RESOLVED",
    "FAILED",
]

Priority = Literal[
    "P1",
    "P2",
    "P3",
    "P4",
]

Channel = Literal[
    "chat",
    "email",
]


router = APIRouter(
    prefix="/api/v1/agent",
    tags=["agent"],
)


@router.get(
    "/tickets",
    response_model=AgentQueueResponse,
)
def read_agent_queue(
    ticket_status: TicketStatus | None = Query(
        default=None,
        alias="status",
    ),
    priority: Priority | None = None,
    intent: str | None = None,
    channel: Channel | None = None,
    assignee_id: UUID | None = None,
    include_resolved: bool = False,
    limit: int = Query(
        default=50,
        ge=1,
        le=100,
    ),
    offset: int = Query(
        default=0,
        ge=0,
    ),
    _user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> AgentQueueResponse:
    try:
        return list_agent_tickets(
            status=ticket_status,
            priority=priority,
            intent=intent,
            channel=channel,
            assignee_id=assignee_id,
            include_resolved=include_resolved,
            limit=limit,
            offset=offset,
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AGENT_QUEUE_UNAVAILABLE",
                "message": (
                    "The support queue is temporarily unavailable."
                ),
            },
        ) from exc


@router.get(
    "/tickets/{ticket_id}",
    response_model=AgentTicketDetail,
)
def read_agent_ticket(
    ticket_id: UUID,
    _user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> AgentTicketDetail:
    try:
        ticket = get_agent_ticket(
            ticket_id
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "AGENT_TICKET_UNAVAILABLE",
                "message": (
                    "The ticket workspace is temporarily unavailable."
                ),
            },
        ) from exc

    if ticket is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "TICKET_NOT_FOUND",
                "message": "Ticket not found.",
            },
        )

    return ticket