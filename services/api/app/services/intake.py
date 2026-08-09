from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.database import get_database_connection
from app.schemas.intake import (
    InboundMessageRequest,
    InboundMessageResponse,
)


def ingest_inbound_message(
    payload: InboundMessageRequest,
) -> InboundMessageResponse:
    """
    Persist one normalized inbound customer message.

    Guarantees:
    - duplicate external messages reuse the original result;
    - one active ticket is reused for the same channel thread;
    - ticket/message creation occurs transactionally;
    - no AI is invoked during intake;
    - a minimal audit event is recorded.
    """

    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.transaction():
            with connection.cursor() as cursor:

                # ------------------------------------------------
                # MESSAGE-LEVEL IDEMPOTENCY LOCK
                #
                # Two workers receiving the same external message
                # simultaneously must not create two processing
                # paths.
                # ------------------------------------------------

                message_lock_key = (
                    f"{payload.channel}:"
                    f"{payload.external_message_id}"
                )

                cursor.execute(
                    """
                    select pg_advisory_xact_lock(
                        hashtextextended(%s, 0)
                    );
                    """,
                    (message_lock_key,),
                )

                # ------------------------------------------------
                # DUPLICATE MESSAGE CHECK
                # ------------------------------------------------

                cursor.execute(
                    """
                    select
                        m.id as message_id,
                        t.id as ticket_id,
                        t.reference as ticket_reference,
                        t.status as ticket_status
                    from public.messages as m
                    join public.tickets as t
                      on t.id = m.ticket_id
                    where m.external_message_id = %s
                    limit 1;
                    """,
                    (payload.external_message_id,),
                )

                existing = cursor.fetchone()

                if existing is not None:
                    return InboundMessageResponse(
                        ticket_id=existing["ticket_id"],
                        ticket_reference=existing[
                            "ticket_reference"
                        ],
                        message_id=existing["message_id"],
                        ticket_status=existing[
                            "ticket_status"
                        ],
                        duplicate=True,
                        created_ticket=False,
                    )

                # ------------------------------------------------
                # THREAD-LEVEL SERIALIZATION
                #
                # This prevents concurrent messages from the same
                # new chat/email thread creating separate tickets.
                # ------------------------------------------------

                if payload.external_thread_id:
                    thread_lock_key = (
                        f"{payload.channel}:thread:"
                        f"{payload.external_thread_id}"
                    )

                    cursor.execute(
                        """
                        select pg_advisory_xact_lock(
                            hashtextextended(%s, 0)
                        );
                        """,
                        (thread_lock_key,),
                    )

                ticket = None

                # ------------------------------------------------
                # REUSE ACTIVE TICKET FOR CHANNEL THREAD
                # ------------------------------------------------

                if payload.external_thread_id:
                    cursor.execute(
                        """
                        select
                            id,
                            reference,
                            status
                        from public.tickets
                        where channel = %s
                          and external_thread_id = %s
                          and status <> 'RESOLVED'
                        order by created_at desc
                        limit 1
                        for update;
                        """,
                        (
                            payload.channel,
                            payload.external_thread_id,
                        ),
                    )

                    ticket = cursor.fetchone()

                created_ticket = False

                # ------------------------------------------------
                # CREATE NEW TICKET
                # ------------------------------------------------

                if ticket is None:
                    cursor.execute(
                        """
                        insert into public.tickets (
                            channel,
                            external_thread_id
                        )
                        values (%s, %s)
                        returning
                            id,
                            reference,
                            status;
                        """,
                        (
                            payload.channel,
                            payload.external_thread_id,
                        ),
                    )

                    ticket = cursor.fetchone()
                    created_ticket = True

                # ------------------------------------------------
                # STORE INBOUND MESSAGE
                # ------------------------------------------------

                attachments = [
                    attachment.model_dump(
                        mode="json"
                    )
                    for attachment in payload.attachments
                ]

                cursor.execute(
                    """
                    insert into public.messages (
                        ticket_id,
                        direction,
                        sender_type,
                        body,
                        external_message_id,
                        subject,
                        customer_hint,
                        sent_at,
                        received_at,
                        attachments,
                        channel_metadata
                    )
                    values (
                        %s,
                        'inbound',
                        'customer',
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                    returning id;
                    """,
                    (
                        ticket["id"],
                        payload.body,
                        payload.external_message_id,
                        payload.subject,
                        payload.customer_hint,
                        payload.received_at,
                        payload.received_at,
                        Jsonb(attachments),
                        Jsonb(payload.metadata),
                    ),
                )

                message = cursor.fetchone()

                # ------------------------------------------------
                # MINIMAL AUDIT EVENT
                #
                # Do not duplicate message bodies or secrets in
                # the audit metadata.
                # ------------------------------------------------

                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,
                        event_type,
                        entity_type,
                        entity_id,
                        metadata
                    )
                    values (
                        'CUSTOMER',
                        null,
                        'INBOUND_MESSAGE_RECEIVED',
                        'message',
                        %s,
                        %s
                    );
                    """,
                    (
                        str(message["id"]),
                        Jsonb(
                            {
                                "channel": payload.channel,
                                "ticket_id": str(
                                    ticket["id"]
                                ),
                                "external_thread_id":
                                    payload.external_thread_id,
                            }
                        ),
                    ),
                )

                return InboundMessageResponse(
                    ticket_id=ticket["id"],
                    ticket_reference=ticket[
                        "reference"
                    ],
                    message_id=message["id"],
                    ticket_status=ticket["status"],
                    duplicate=False,
                    created_ticket=created_ticket,
                )