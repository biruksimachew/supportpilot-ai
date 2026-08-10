from uuid import UUID

from psycopg.rows import dict_row

from app.core.database import (
    get_database_connection,
)
from app.schemas.agent import (
    AgentAuditEvent,
    AgentOrderSummary,
    AgentQueueItem,
    AgentQueueResponse,
    AgentTicketDetail,
    AgentTicketMessage,
)


def list_agent_tickets(
    *,
    status: str | None = None,
    priority: str | None = None,
    intent: str | None = None,
    channel: str | None = None,
    assignee_id: UUID | None = None,
    include_resolved: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> AgentQueueResponse:
    filters: list[str] = []
    parameters: list[object] = []

    if not include_resolved:
        filters.append(
            "t.status <> 'RESOLVED'"
        )

    if status is not None:
        filters.append(
            "t.status = %s"
        )
        parameters.append(status)

    if priority is not None:
        filters.append(
            "t.priority = %s"
        )
        parameters.append(priority)

    if intent is not None:
        filters.append(
            "t.intent = %s"
        )
        parameters.append(intent)

    if channel is not None:
        filters.append(
            "t.channel = %s"
        )
        parameters.append(channel)

    if assignee_id is not None:
        filters.append(
            "t.assignee_id = %s"
        )
        parameters.append(
            assignee_id
        )

    where_clause = ""

    if filters:
        where_clause = (
            "where "
            + " and ".join(filters)
        )

    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                select count(*) as total
                from public.tickets as t
                {where_clause};
                """,
                tuple(parameters),
            )

            total = cursor.fetchone()[
                "total"
            ]

            query_parameters = [
                *parameters,
                limit,
                offset,
            ]

            cursor.execute(
                f"""
                select
                    t.id,
                    t.reference,
                    t.channel,
                    t.status,
                    t.priority,
                    t.intent,
                    t.confidence_band,

                    c.name
                        as customer_name,
                    c.email
                        as customer_email,

                    assignee.name
                        as assignee_name,

                    t.created_at,
                    t.updated_at,

                    (
                        select count(*)
                        from public.messages as count_message
                        where count_message.ticket_id = t.id
                    ) as message_count,

                    latest.body
                        as last_message_body,
                    latest.received_at
                        as last_message_at

                from public.tickets as t

                left join public.customers as c
                    on c.id = t.customer_ref

                left join public.users as assignee
                    on assignee.id = t.assignee_id

                left join lateral (
                    select
                        m.body,
                        m.received_at
                    from public.messages as m
                    where m.ticket_id = t.id
                    order by
                        m.received_at desc,
                        m.created_at desc,
                        m.id desc
                    limit 1
                ) as latest
                    on true

                {where_clause}

                order by
                    case t.priority
                        when 'P1' then 1
                        when 'P2' then 2
                        when 'P3' then 3
                        when 'P4' then 4
                        else 5
                    end,
                    t.updated_at desc

                limit %s
                offset %s;
                """,
                tuple(
                    query_parameters
                ),
            )

            items = [
                AgentQueueItem(
                    **row
                )
                for row
                in cursor.fetchall()
            ]

    return AgentQueueResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


def get_agent_ticket(
    ticket_id: UUID,
) -> AgentTicketDetail | None:
    with get_database_connection() as connection:
        connection.row_factory = dict_row

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    t.id,
                    t.reference,
                    t.channel,
                    t.status,
                    t.priority,
                    t.intent,
                    t.confidence_band,
                    t.restricted_action,
                    t.escalation_reason,
                    t.resolution_code,
                    t.created_at,
                    t.updated_at,
                    t.resolved_at,

                    c.id
                        as customer_id,
                    c.name
                        as customer_name,
                    c.email
                        as customer_email,

                    assignee.id
                        as assignee_id,
                    assignee.name
                        as assignee_name

                from public.tickets as t

                left join public.customers as c
                    on c.id = t.customer_ref

                left join public.users as assignee
                    on assignee.id = t.assignee_id

                where t.id = %s
                limit 1;
                """,
                (ticket_id,),
            )

            ticket = cursor.fetchone()

            if ticket is None:
                return None

            cursor.execute(
                """
                select
                    id,
                    direction,
                    sender_type,
                    body,
                    is_internal,
                    sent_at,
                    received_at
                from public.messages
                where ticket_id = %s
                order by
                    received_at,
                    created_at,
                    id;
                """,
                (ticket_id,),
            )

            messages = [
                AgentTicketMessage(
                    **row
                )
                for row
                in cursor.fetchall()
            ]

            orders: list[
                AgentOrderSummary
            ] = []

            if (
                ticket["customer_id"]
                is not None
            ):
                cursor.execute(
                    """
                    select
                        external_order_id,
                        status,
                        fulfillment_summary,
                        total_summary,
                        retrieved_at
                    from public.orders_cache
                    where customer_ref = %s
                    order by retrieved_at desc;
                    """,
                    (
                        ticket[
                            "customer_id"
                        ],
                    ),
                )

                orders = [
                    AgentOrderSummary(
                        **row
                    )
                    for row
                    in cursor.fetchall()
                ]

            cursor.execute(
                """
                select
                    id,
                    actor_type,
                    event_type,
                    entity_type,
                    entity_id,
                    metadata,
                    created_at
                from public.audit_events
                where (
                    entity_type = 'ticket'
                    and entity_id = %s
                )
                or (
                    metadata ->> 'ticket_id'
                    = %s
                )
                order by created_at;
                """,
                (
                    str(ticket_id),
                    str(ticket_id),
                ),
            )

            audit_events = [
                AgentAuditEvent(
                    **row
                )
                for row
                in cursor.fetchall()
            ]

    return AgentTicketDetail(
        **ticket,
        messages=messages,
        orders=orders,
        audit_events=audit_events,
    )