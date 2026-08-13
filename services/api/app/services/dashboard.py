from datetime import (
    datetime,
    timezone,
)

from psycopg.rows import (
    dict_row,
)

from app.core.database import (
    get_database_connection,
)

from app.schemas.dashboard import (
    AgentDashboardResponse,
    DashboardActivityItem,
    DashboardAISummary,
    DashboardDeliverySummary,
    DashboardDistributionItem,
    DashboardQueueSummary,
    DashboardResolutionSummary,
)


def _distribution(
    rows: list[dict],
) -> list[
    DashboardDistributionItem
]:

    return [
        DashboardDistributionItem(
            key=
                str(
                    row["key"]
                ),

            count=
                int(
                    row["count"]
                ),
        )

        for row in rows
    ]


def get_agent_dashboard(
) -> AgentDashboardResponse:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.cursor() as cursor:

            # ==================================================
            # Queue health
            # ==================================================

            cursor.execute(
                """
                select
                    count(*)
                        filter (
                            where status
                            <> 'RESOLVED'
                        )
                        as open_tickets,

                    count(*)
                        filter (
                            where status
                            = 'REVIEW_REQUIRED'
                        )
                        as review_required,

                    count(*)
                        filter (
                            where status
                            = 'WAITING_CUSTOMER'
                        )
                        as waiting_customer,

                    count(*)
                        filter (
                            where status
                            = 'DRAFTED'
                        )
                        as drafted,

                    count(*)
                        filter (
                            where status
                            = 'NEW'
                        )
                        as new_tickets,

                    count(*)
                        filter (
                            where
                                status
                                <> 'RESOLVED'

                                and priority
                                in (
                                    'P1',
                                    'P2'
                                )
                        )
                        as urgent_p1_p2,

                    count(*)
                        filter (
                            where
                                status
                                <> 'RESOLVED'

                                and assignee_id
                                is null
                        )
                        as unassigned,

                    count(*)
                        filter (
                            where
                                status
                                <> 'RESOLVED'

                                and restricted_action
                                = true
                        )
                        as restricted_open

                from public.tickets;
                """
            )


            queue_row = (
                cursor.fetchone()
            )


            # ==================================================
            # Ticket status distribution
            # ==================================================

            cursor.execute(
                """
                select
                    status as key,
                    count(*) as count

                from public.tickets

                group by status

                order by
                    case status
                        when 'NEW' then 1
                        when 'TRIAGED' then 2
                        when 'DRAFTED' then 3
                        when 'REVIEW_REQUIRED' then 4
                        when 'WAITING_CUSTOMER' then 5
                        when 'AUTO_RESPONDED' then 6
                        when 'RESOLVED' then 7
                        when 'FAILED' then 8
                        else 9
                    end;
                """
            )


            status_breakdown = (
                _distribution(
                    cursor.fetchall()
                )
            )


            # ==================================================
            # Priority distribution — open work only
            # ==================================================

            cursor.execute(
                """
                select
                    priority as key,
                    count(*) as count

                from public.tickets

                where status <> 'RESOLVED'

                group by priority

                order by
                    case priority
                        when 'P1' then 1
                        when 'P2' then 2
                        when 'P3' then 3
                        when 'P4' then 4
                        else 5
                    end;
                """
            )


            priority_breakdown = (
                _distribution(
                    cursor.fetchall()
                )
            )


            # ==================================================
            # Channel distribution — open work only
            # ==================================================

            cursor.execute(
                """
                select
                    channel as key,
                    count(*) as count

                from public.tickets

                where status <> 'RESOLVED'

                group by channel

                order by channel;
                """
            )


            channel_breakdown = (
                _distribution(
                    cursor.fetchall()
                )
            )


            # ==================================================
            # Intent distribution — open work only
            # ==================================================

            cursor.execute(
                """
                select
                    intent as key,
                    count(*) as count

                from public.tickets

                where
                    status <> 'RESOLVED'

                    and intent
                    is not null

                group by intent

                order by
                    count(*) desc,
                    intent

                limit 8;
                """
            )


            intent_breakdown = (
                _distribution(
                    cursor.fetchall()
                )
            )


            # ==================================================
            # Escalation reasons
            # ==================================================

            cursor.execute(
                """
                select
                    escalation_reason as key,
                    count(*) as count

                from public.tickets

                where
                    status <> 'RESOLVED'

                    and escalation_reason
                    is not null

                    and trim(
                        escalation_reason
                    ) <> ''

                group by
                    escalation_reason

                order by
                    count(*) desc,
                    escalation_reason

                limit 8;
                """
            )


            escalation_breakdown = (
                _distribution(
                    cursor.fetchall()
                )
            )


            # ==================================================
            # AI decision health
            # ==================================================

            cursor.execute(
                """
                select
                    count(*)
                        as total_runs,

                    count(*)
                        filter (
                            where decision
                            = 'AUTO_RESPOND'
                        )
                        as auto_respond,

                    count(*)
                        filter (
                            where decision
                            = 'REVIEW_REQUIRED'
                        )
                        as review_required,

                    count(*)
                        filter (
                            where decision
                            = 'REQUEST_CLARIFICATION'
                        )
                        as request_clarification,

                    count(*)
                        filter (
                            where decision
                            = 'FAILED'
                        )
                        as failed

                from public.ai_runs;
                """
            )


            ai_row = (
                cursor.fetchone()
            )


            total_ai_runs = int(
                ai_row[
                    "total_runs"
                ]
            )


            automation_rate = (
                round(
                    (
                        int(
                            ai_row[
                                "auto_respond"
                            ]
                        )
                        / total_ai_runs
                    )
                    * 100,
                    1,
                )

                if total_ai_runs > 0

                else None
            )


            # ==================================================
            # Delivery health
            # ==================================================

            cursor.execute(
                """
                select
                    count(*)
                        as total_deliveries,

                    count(*)
                        filter (
                            where status
                            = 'DELIVERED'
                        )
                        as delivered,

                    count(*)
                        filter (
                            where status
                            = 'FAILED'
                        )
                        as failed,

                    count(*)
                        filter (
                            where status
                            = 'UNCERTAIN'
                        )
                        as uncertain,

                    count(*)
                        filter (
                            where status
                            = 'PENDING'
                        )
                        as pending

                from public.outbound_deliveries;
                """
            )


            delivery_row = (
                cursor.fetchone()
            )


            total_deliveries = int(
                delivery_row[
                    "total_deliveries"
                ]
            )


            delivery_success_rate = (
                round(
                    (
                        int(
                            delivery_row[
                                "delivered"
                            ]
                        )
                        / total_deliveries
                    )
                    * 100,
                    1,
                )

                if total_deliveries > 0

                else None
            )


            # ==================================================
            # Resolution health
            # ==================================================

            cursor.execute(
                """
                select
                    count(*)
                        filter (
                            where status
                            = 'RESOLVED'
                        )
                        as resolved_tickets,

                    avg(
                        extract(
                            epoch from (
                                resolved_at
                                - created_at
                            )
                        )
                        / 60.0
                    )
                        filter (
                            where
                                status
                                = 'RESOLVED'

                                and resolved_at
                                is not null
                        )
                        as average_resolution_minutes

                from public.tickets;
                """
            )


            resolution_row = (
                cursor.fetchone()
            )


            average_resolution = (
                round(
                    float(
                        resolution_row[
                            "average_resolution_minutes"
                        ]
                    ),
                    1,
                )

                if resolution_row[
                    "average_resolution_minutes"
                ]
                is not None

                else None
            )


            # ==================================================
            # Recent operational activity
            # ==================================================

            cursor.execute(
                """
                select
                    ae.id,
                    ae.actor_type,
                    ae.event_type,

                    t.id
                        as ticket_id,

                    t.reference
                        as ticket_reference,

                    ae.created_at

                from public.audit_events as ae

                left join public.tickets as t
                    on (
                        ae.entity_type = 'ticket'

                        and ae.entity_id
                            = t.id::text
                    )

                    or (
                        ae.metadata
                            ->> 'ticket_id'
                            = t.id::text
                    )

                where t.id
                    is not null

                order by
                    ae.created_at desc,
                    ae.id desc

                limit 12;
                """
            )


            recent_activity = [
                DashboardActivityItem(
                    **row
                )

                for row
                in cursor.fetchall()
            ]


    return AgentDashboardResponse(
        generated_at=
            datetime.now(
                timezone.utc
            ),

        queue=
            DashboardQueueSummary(
                **queue_row
            ),

        status_breakdown=
            status_breakdown,

        priority_breakdown=
            priority_breakdown,

        channel_breakdown=
            channel_breakdown,

        intent_breakdown=
            intent_breakdown,

        escalation_breakdown=
            escalation_breakdown,

        ai=
            DashboardAISummary(
                total_runs=
                    total_ai_runs,

                auto_respond=
                    int(
                        ai_row[
                            "auto_respond"
                        ]
                    ),

                review_required=
                    int(
                        ai_row[
                            "review_required"
                        ]
                    ),

                request_clarification=
                    int(
                        ai_row[
                            "request_clarification"
                        ]
                    ),

                failed=
                    int(
                        ai_row[
                            "failed"
                        ]
                    ),

                automation_rate_pct=
                    automation_rate,
            ),

        delivery=
            DashboardDeliverySummary(
                total_deliveries=
                    total_deliveries,

                delivered=
                    int(
                        delivery_row[
                            "delivered"
                        ]
                    ),

                failed=
                    int(
                        delivery_row[
                            "failed"
                        ]
                    ),

                uncertain=
                    int(
                        delivery_row[
                            "uncertain"
                        ]
                    ),

                pending=
                    int(
                        delivery_row[
                            "pending"
                        ]
                    ),

                delivery_success_rate_pct=
                    delivery_success_rate,
            ),

        resolution=
            DashboardResolutionSummary(
                resolved_tickets=
                    int(
                        resolution_row[
                            "resolved_tickets"
                        ]
                    ),

                average_resolution_minutes=
                    average_resolution,
            ),

        recent_activity=
            recent_activity,
    )