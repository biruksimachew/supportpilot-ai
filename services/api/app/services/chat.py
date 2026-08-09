from datetime import datetime, timezone
from uuid import UUID

from psycopg.rows import dict_row

from app.core.database import (
    get_database_connection,
)
from app.schemas.chat import (
    ChatHistoryMessage,
    ChatHistoryResponse,
    ChatMessageRequest,
    ChatMessageResponse,
)
from app.schemas.intake import (
    InboundMessageRequest,
)
from app.services.intake import (
    ingest_inbound_message,
)


def send_chat_message(
    session_id: UUID,
    payload: ChatMessageRequest,
) -> ChatMessageResponse:
    external_message_id = (
        f"chat:{session_id}:"
        f"{payload.client_message_id}"
    )

    intake_payload = InboundMessageRequest(
        channel="chat",
        external_message_id=external_message_id,
        external_thread_id=str(session_id),
        customer_hint=payload.customer_hint,
        subject=None,
        body=payload.body,
        received_at=datetime.now(
            timezone.utc
        ),
        attachments=[],
        metadata={
            "adapter": "website_chat",
            "client_message_id": str(
                payload.client_message_id
            ),
        },
    )

    result = ingest_inbound_message(
        intake_payload
    )

    return ChatMessageResponse(
        ticket_id=result.ticket_id,
        ticket_reference=result.ticket_reference,
        ticket_status=result.ticket_status,
        message_id=result.message_id,
        duplicate=result.duplicate,
        created_ticket=result.created_ticket,
    )


def get_chat_history(
    session_id: UUID,
) -> ChatHistoryResponse:
    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            # Latest ticket represents current state.
            cursor.execute(
                """
                select
                    id,
                    reference,
                    status
                from public.tickets
                where channel = 'chat'
                  and external_thread_id = %s
                order by created_at desc
                limit 1;
                """,
                (str(session_id),),
            )

            latest_ticket = cursor.fetchone()

            if latest_ticket is None:
                return ChatHistoryResponse(
                    session_id=session_id,
                    ticket_reference=None,
                    ticket_status=None,
                    messages=[],
                )

            # Preserve browser-session conversation history even
            # if a later message eventually creates a new ticket
            # after an earlier ticket has been resolved.
            cursor.execute(
                """
                select
                    m.id,
                    m.direction,
                    m.sender_type,
                    m.body,
                    m.sent_at
                from public.messages as m
                join public.tickets as t
                  on t.id = m.ticket_id
                where t.channel = 'chat'
                  and t.external_thread_id = %s
                  and m.is_internal = false
                order by
                    m.received_at,
                    m.created_at,
                    m.id;
                """,
                (str(session_id),),
            )

            messages = [
                ChatHistoryMessage(
                    id=row["id"],
                    direction=row["direction"],
                    sender_type=row["sender_type"],
                    body=row["body"],
                    sent_at=row["sent_at"],
                )
                for row in cursor.fetchall()
            ]

    return ChatHistoryResponse(
        session_id=session_id,
        ticket_reference=latest_ticket[
            "reference"
        ],
        ticket_status=latest_ticket[
            "status"
        ],
        messages=messages,
    )