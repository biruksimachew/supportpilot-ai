from uuid import UUID

from psycopg.rows import dict_row

from app.core.database import (
    get_database_connection,
)

from app.schemas.agent import (
    AgentAIRunSummary,
    AgentAuditEvent,
    AgentOrderSummary,
    AgentQueueItem,
    AgentQueueResponse,
    AgentRetrievalEvidence,
    AgentTicketDetail,
    AgentTicketMessage,
    AgentToolCall,
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

        parameters.append(
            status
        )


    if priority is not None:
        filters.append(
            "t.priority = %s"
        )

        parameters.append(
            priority
        )


    if intent is not None:
        filters.append(
            "t.intent = %s"
        )

        parameters.append(
            intent
        )


    if channel is not None:
        filters.append(
            "t.channel = %s"
        )

        parameters.append(
            channel
        )


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
            + " and ".join(
                filters
            )
        )


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.cursor() as cursor:

            cursor.execute(
                f"""
                select
                    count(*) as total

                from public.tickets as t

                {where_clause};
                """,
                tuple(
                    parameters
                ),
            )


            total = (
                cursor.fetchone()[
                    "total"
                ]
            )


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

                        from public.messages
                            as count_message

                        where
                            count_message.ticket_id
                            = t.id
                    ) as message_count,

                    latest.body
                        as last_message_body,

                    latest.received_at
                        as last_message_at

                from public.tickets as t

                left join public.customers as c
                    on c.id =
                        t.customer_ref

                left join public.users as assignee
                    on assignee.id =
                        t.assignee_id

                left join lateral (
                    select
                        m.body,
                        m.received_at

                    from public.messages as m

                    where
                        m.ticket_id = t.id

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


def _safe_draft_ready(
    decision_reasons: list[str],
) -> bool:

    return (
        "SAFE_KNOWLEDGE_DRAFT"
        in decision_reasons

        or

        "SAFE_COMMERCE_DRAFT"
        in decision_reasons
    )


def get_agent_ticket(
    ticket_id: UUID,
) -> AgentTicketDetail | None:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.cursor() as cursor:

            # ==================================================
            # Ticket and customer context
            # ==================================================

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

                    t.identity_verification_status,

                    t.identity_verification_method,

                    t.identity_verified_at,

                    t.identity_verified_order_number,

                    t.identity_verification_attempts,

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
                    on c.id =
                        t.customer_ref

                left join public.users as assignee
                    on assignee.id =
                        t.assignee_id

                where t.id = %s

                limit 1;
                """,
                (
                    ticket_id,
                ),
            )


            ticket = (
                cursor.fetchone()
            )


            if ticket is None:
                return None


            # ==================================================
            # Conversation
            # ==================================================

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
                (
                    ticket_id,
                ),
            )


            messages = [
                AgentTicketMessage(
                    **row
                )

                for row
                in cursor.fetchall()
            ]


            # ==================================================
            # Commerce context
            # ==================================================

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

                    order by
                        retrieved_at desc;
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


            # ==================================================
            # Latest AI run
            # ==================================================

            cursor.execute(
                """
                select
                    ar.id,
                    ar.message_id,

                    source_message.body
                        as source_message_body,

                    ar.provider,
                    ar.model,

                    ar.prompt_version,

                    ar.intent,

                    ar.confidence,
                    ar.confidence_band,

                    ar.decision,
                    ar.decision_reasons,

                    ar.latency_ms,
                    ar.error_code,

                    ar.created_at

                from public.ai_runs as ar

                left join public.messages
                    as source_message

                    on source_message.id =
                        ar.message_id

                where ar.ticket_id = %s

                order by
                    ar.created_at desc,
                    ar.id desc

                limit 1;
                """,
                (
                    ticket_id,
                ),
            )


            ai_run_row = (
                cursor.fetchone()
            )


            latest_ai_run: (
                AgentAIRunSummary | None
            ) = None


            retrieval_evidence: list[
                AgentRetrievalEvidence
            ] = []


            tool_calls: list[
                AgentToolCall
            ] = []


            if ai_run_row is not None:

                reasons = list(
                    ai_run_row[
                        "decision_reasons"
                    ]
                    or []
                )


                ai_run_payload = dict(
                    ai_run_row
                )


                ai_run_payload[
                    "decision_reasons"
                ] = reasons


                latest_ai_run = (
                    AgentAIRunSummary(
                        **ai_run_payload,

                        safe_draft_ready=
                            _safe_draft_ready(
                                reasons
                            ),

                        auto_response_eligible=
                            (
                                ai_run_row[
                                    "decision"
                                ]
                                == "AUTO_RESPOND"
                            ),
                    )
                )


                # ==============================================
                # Retrieval evidence for latest AI run
                # ==============================================

                cursor.execute(
                    """
                    select
                        kc.id
                            as chunk_id,

                        re.rank,
                        re.score,

                        kc.section,
                        kc.content,

                        ks.id
                            as source_id,

                        ks.title
                            as source_title,

                        ks.type
                            as source_type,

                        ks.version
                            as source_version,

                        ks.status
                            as source_status,

                        ks.effective_at
                            as source_effective_at

                    from public.retrieval_evidence
                        as re

                    join public.knowledge_chunks
                        as kc

                        on kc.id =
                            re.chunk_id

                    join public.knowledge_sources
                        as ks

                        on ks.id =
                            kc.source_id

                    where re.ai_run_id = %s

                    order by
                        re.rank,
                        kc.id;
                    """,
                    (
                        ai_run_row[
                            "id"
                        ],
                    ),
                )


                retrieval_evidence = [
                    AgentRetrievalEvidence(
                        **row
                    )

                    for row
                    in cursor.fetchall()
                ]


                # ==============================================
                # Tool calls for latest AI run
                # ==============================================

                cursor.execute(
                    """
                    select
                        id,

                        tool_name,

                        safe_request_summary,
                        result_summary,

                        status,
                        latency_ms,

                        created_at

                    from public.tool_calls

                    where ai_run_id = %s

                    order by
                        created_at,
                        id;
                    """,
                    (
                        ai_run_row[
                            "id"
                        ],
                    ),
                )


                tool_calls = [
                    AgentToolCall(
                        **row
                    )

                    for row
                    in cursor.fetchall()
                ]


            # ==================================================
            # Audit timeline
            # ==================================================

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

                order by
                    created_at,
                    id;
                """,
                (
                    str(
                        ticket_id
                    ),

                    str(
                        ticket_id
                    ),
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

        messages=
            messages,

        orders=
            orders,

        latest_ai_run=
            latest_ai_run,

        retrieval_evidence=
            retrieval_evidence,

        tool_calls=
            tool_calls,

        audit_events=
            audit_events,
    )