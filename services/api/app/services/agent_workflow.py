from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.evidence_decision import (
    TicketAIDraftResponse,
)

from app.schemas.agent_workflow import (
    AgentWorkflowResponse,
)


class AgentTicketNotFoundError(
    LookupError
):
    pass


class AgentWorkflowConflictError(
    RuntimeError
):
    pass


def _actor_type(
    user: InternalUser,
) -> str:

    mapping = {
        "SUPPORT_AGENT":
            "AGENT",

        "SUPPORT_MANAGER":
            "MANAGER",

        "SYSTEM_ADMIN":
            "ADMIN",
    }

    return mapping[
        user.role
    ]

def _load_ticket_for_update(
    cursor,
    *,
    ticket_id: UUID,
) -> dict:

    cursor.execute(
        """
        select
            id,
            status,
            priority,

            assignee_id,

            escalation_reason,
            resolution_code,

            restricted_action

        from public.tickets

        where id = %s

        for update;
        """,
        (
            ticket_id,
        ),
    )

    row = cursor.fetchone()

    if row is None:
        raise AgentTicketNotFoundError(
            "Ticket not found."
        )

    return row


def _insert_agent_action(
    cursor,
    *,
    user: InternalUser,

    ticket_id: UUID,

    action: str,

    before_value:
        dict | None,

    after_value:
        dict | None,
) -> UUID:

    # Real authenticated staff are backed by
    # public.users. The subquery also keeps
    # dependency-overridden integration tests
    # compatible with nullable user_id.
    cursor.execute(
        """
        insert into public.agent_actions (
            ticket_id,
            user_id,

            action,

            before_value,
            after_value
        )

        values (
            %s,

            (
                select id
                from public.users
                where id = %s
                limit 1
            ),

            %s,

            %s,
            %s
        )

        returning id;
        """,
        (
            ticket_id,
            user.id,

            action,

            (
                Jsonb(before_value)
                if before_value
                is not None
                else None
            ),

            (
                Jsonb(after_value)
                if after_value
                is not None
                else None
            ),
        ),
    )

    return cursor.fetchone()[
        "id"
    ]


def _insert_user_audit(
    cursor,
    *,
    user: InternalUser,

    ticket_id: UUID,

    event_type: str,

    metadata: dict,
) -> None:

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
            %s,
            %s,

            %s,

            'ticket',
            %s,

            %s
        );
        """,
        (
            _actor_type(
                user
            ),

            str(
                user.id
            ),

            event_type,

            str(
                ticket_id
            ),

            Jsonb(
                
                {
                    "ticket_id":
                        str(
                            ticket_id
                        ),

                    "actor_email":
                        user.email,

                    "actor_role":
                        user.role,

                    **metadata,
                }
            ),
        ),
    )


def capture_ai_draft(
    *,
    user: InternalUser,

    result:
        TicketAIDraftResponse,
) -> UUID:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )

        with connection.transaction():

            with connection.cursor() as cursor:

                # Confirm the AI run belongs to the
                # exact ticket/message pair returned
                # by the support pipeline.
                cursor.execute(
                    """
                    select id

                    from public.ai_runs

                    where id = %s
                      and ticket_id = %s
                      and message_id = %s

                    limit 1;
                    """,
                    (
                        result.ai_run_id,
                        result.ticket_id,
                        result.message_id,
                    ),
                )

                if (
                    cursor.fetchone()
                    is None
                ):
                    raise (
                        AgentWorkflowConflictError(
                            (
                                "AI draft scope "
                                "could not be verified."
                            )
                        )
                    )


                # Idempotent per AI run.
                cursor.execute(
                    """
                    select id

                    from public.agent_actions

                    where
                        ticket_id = %s

                        and action =
                            'AI_DRAFT_CAPTURED'

                        and (
                            after_value
                            ->> 'ai_run_id'
                        ) = %s

                    order by created_at desc

                    limit 1;
                    """,
                    (
                        result.ticket_id,

                        str(
                            result.ai_run_id
                        ),
                    ),
                )

                existing = (
                    cursor.fetchone()
                )

                if existing is not None:
                    return existing["id"]


                action_id = (
                    _insert_agent_action(
                        cursor,

                        user=user,

                        ticket_id=
                            result.ticket_id,

                        action=
                            "AI_DRAFT_CAPTURED",

                        before_value=None,

                        after_value={
                            "ai_run_id":
                                str(
                                    result.ai_run_id
                                ),

                            "source_message_id":
                                str(
                                    result.message_id
                                ),

                            "answer_status":
                                result
                                .answer
                                .status,

                            "original_body":
                                result
                                .answer
                                .answer,

                            "decision":
                                result.decision,

                            "decision_reasons":
                                result
                                .decision_reasons,

                            "confidence":
                                result.confidence,

                            "confidence_band":
                                result
                                .confidence_band,

                            "generation_attempted":
                                result
                                .generation_attempted,

                            "safe_draft_ready":
                                result
                                .safe_draft_ready,
                        },
                    )
                )


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
                        'AI',
                        %s,

                        'AI_DRAFT_CAPTURED',

                        'ai_run',
                        %s,

                        %s
                    );
                    """,
                    (
                        str(
                            result.ai_run_id
                        ),

                        str(
                            result.ai_run_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        result.ticket_id
                                    ),

                                "message_id":
                                    str(
                                        result.message_id
                                    ),

                                "agent_action_id":
                                    str(
                                        action_id
                                    ),

                                "requested_by":
                                    str(
                                        user.id
                                    ),

                                "decision":
                                    result.decision,

                                "safe_draft_ready":
                                    result
                                    .safe_draft_ready,
                            }
                        ),
                    ),
                )


    return action_id


def add_internal_note(
    *,
    user: InternalUser,

    ticket_id: UUID,

    body: str,
) -> AgentWorkflowResponse:

    body = body.strip()

    if not body:
        raise ValueError(
            "Internal note cannot be empty."
        )


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                ticket = (
                    _load_ticket_for_update(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise (
                        AgentWorkflowConflictError(
                            (
                                "Resolved tickets "
                                "cannot be modified."
                            )
                        )
                    )


                cursor.execute(
                    """
                    insert into public.messages (
                        ticket_id,

                        direction,
                        sender_type,

                        body,

                        is_internal,

                        channel_metadata
                    )

                    values (
                        %s,

                        'outbound',
                        'agent',

                        %s,

                        true,

                        %s
                    )

                    returning id;
                    """,
                    (
                        ticket_id,

                        body,

                        Jsonb(
                            {
                                "adapter":
                                    "agent_console",

                                "visibility":
                                    "internal",

                                "actor_id":
                                    str(
                                        user.id
                                    ),
                            }
                        ),
                    ),
                )


                message_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                action_id = (
                    _insert_agent_action(
                        cursor,

                        user=user,

                        ticket_id=
                            ticket_id,

                        action=
                            "INTERNAL_NOTE_ADDED",

                        before_value={
                            "status":
                                ticket[
                                    "status"
                                ],
                        },

                        after_value={
                            "message_id":
                                str(
                                    message_id
                                ),

                            "body_length":
                                len(body),

                            "status":
                                ticket[
                                    "status"
                                ],
                        },
                    )
                )


                _insert_user_audit(
                    cursor,

                    user=user,

                    ticket_id=
                        ticket_id,

                    event_type=
                        "INTERNAL_NOTE_ADDED",

                    metadata={
                        "message_id":
                            str(
                                message_id
                            ),

                        "agent_action_id":
                            str(
                                action_id
                            ),
                    },
                )


    return AgentWorkflowResponse(
        ticket_id=
            ticket_id,

        action_id=
            action_id,

        status=
            ticket[
                "status"
            ],

        assignee_id=
            ticket[
                "assignee_id"
            ],

        message_id=
            message_id,

        escalation_reason=
            ticket[
                "escalation_reason"
            ],

        resolution_code=
            ticket[
                "resolution_code"
            ],
    )


def assign_ticket_to_self(
    *,
    user: InternalUser,

    ticket_id: UUID,
) -> AgentWorkflowResponse:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                ticket = (
                    _load_ticket_for_update(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise (
                        AgentWorkflowConflictError(
                            (
                                "Resolved tickets "
                                "cannot be assigned."
                            )
                        )
                    )


                cursor.execute(
                    """
                    select id

                    from public.users

                    where id = %s

                      and status =
                          'ACTIVE'

                      and role in (
                          'SUPPORT_AGENT',
                          'SUPPORT_MANAGER',
                          'SYSTEM_ADMIN'
                      )

                    limit 1;
                    """,
                    (
                        user.id,
                    ),
                )


                if (
                    cursor.fetchone()
                    is None
                ):
                    raise (
                        AgentWorkflowConflictError(
                            (
                                "The authenticated "
                                "staff profile is "
                                "not active."
                            )
                        )
                    )


                cursor.execute(
                    """
                    update public.tickets

                    set assignee_id = %s

                    where id = %s;
                    """,
                    (
                        user.id,
                        ticket_id,
                    ),
                )


                action_id = (
                    _insert_agent_action(
                        cursor,

                        user=user,

                        ticket_id=
                            ticket_id,

                        action=
                            "TICKET_ASSIGNED",

                        before_value={
                            "assignee_id":
                                (
                                    str(
                                        ticket[
                                            "assignee_id"
                                        ]
                                    )
                                    if ticket[
                                        "assignee_id"
                                    ]
                                    is not None

                                    else None
                                ),
                        },

                        after_value={
                            "assignee_id":
                                str(
                                    user.id
                                ),
                        },
                    )
                )


                _insert_user_audit(
                    cursor,

                    user=user,

                    ticket_id=
                        ticket_id,

                    event_type=
                        "TICKET_ASSIGNED",

                    metadata={
                        "agent_action_id":
                            str(
                                action_id
                            ),

                        "assignee_id":
                            str(
                                user.id
                            ),
                    },
                )


    return AgentWorkflowResponse(
        ticket_id=
            ticket_id,

        action_id=
            action_id,

        status=
            ticket[
                "status"
            ],

        assignee_id=
            user.id,

        escalation_reason=
            ticket[
                "escalation_reason"
            ],

        resolution_code=
            ticket[
                "resolution_code"
            ],
    )


def escalate_ticket(
    *,
    user: InternalUser,

    ticket_id: UUID,

    reason: str,

    priority:
        str | None = None,
) -> AgentWorkflowResponse:

    reason = reason.strip()

    if not reason:
        raise ValueError(
            "Escalation reason cannot be empty."
        )


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                ticket = (
                    _load_ticket_for_update(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise (
                        AgentWorkflowConflictError(
                            (
                                "Resolved tickets "
                                "cannot be escalated."
                            )
                        )
                    )


                resulting_priority = (
                    priority
                    or ticket[
                        "priority"
                    ]
                )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        status =
                            'REVIEW_REQUIRED',

                        priority =
                            %s,

                        escalation_reason =
                            %s

                    where id = %s;
                    """,
                    (
                        resulting_priority,

                        reason,

                        ticket_id,
                    ),
                )


                action_id = (
                    _insert_agent_action(
                        cursor,

                        user=user,

                        ticket_id=
                            ticket_id,

                        action=
                            "TICKET_ESCALATED",

                        before_value={
                            "status":
                                ticket[
                                    "status"
                                ],

                            "priority":
                                ticket[
                                    "priority"
                                ],

                            "escalation_reason":
                                ticket[
                                    "escalation_reason"
                                ],
                        },

                        after_value={
                            "status":
                                "REVIEW_REQUIRED",

                            "priority":
                                resulting_priority,

                            "escalation_reason":
                                reason,
                        },
                    )
                )


                _insert_user_audit(
                    cursor,

                    user=user,

                    ticket_id=
                        ticket_id,

                    event_type=
                        "TICKET_ESCALATED",

                    metadata={
                        "agent_action_id":
                            str(
                                action_id
                            ),

                        "priority":
                            resulting_priority,

                        "reason":
                            reason,
                    },
                )


    return AgentWorkflowResponse(
        ticket_id=
            ticket_id,

        action_id=
            action_id,

        status=
            "REVIEW_REQUIRED",

        assignee_id=
            ticket[
                "assignee_id"
            ],

        escalation_reason=
            reason,

        resolution_code=None,
    )


def resolve_ticket(
    *,
    user: InternalUser,

    ticket_id: UUID,

    resolution_code: str,
) -> AgentWorkflowResponse:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                ticket = (
                    _load_ticket_for_update(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise (
                        AgentWorkflowConflictError(
                            "Ticket is already resolved."
                        )
                    )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        status =
                            'RESOLVED',

                        resolution_code =
                            %s,

                        resolved_at =
                            timezone(
                                'utc',
                                now()
                            ),

                        escalation_reason =
                            null

                    where id = %s;
                    """,
                    (
                        resolution_code,
                        ticket_id,
                    ),
                )


                action_id = (
                    _insert_agent_action(
                        cursor,

                        user=user,

                        ticket_id=
                            ticket_id,

                        action=
                            "TICKET_RESOLVED",

                        before_value={
                            "status":
                                ticket[
                                    "status"
                                ],

                            "resolution_code":
                                ticket[
                                    "resolution_code"
                                ],

                            "escalation_reason":
                                ticket[
                                    "escalation_reason"
                                ],
                        },

                        after_value={
                            "status":
                                "RESOLVED",

                            "resolution_code":
                                resolution_code,

                            "escalation_reason":
                                None,
                        },
                    )
                )


                _insert_user_audit(
                    cursor,

                    user=user,

                    ticket_id=
                        ticket_id,

                    event_type=
                        "TICKET_RESOLVED",

                    metadata={
                        "agent_action_id":
                            str(
                                action_id
                            ),

                        "resolution_code":
                            resolution_code,
                    },
                )


    return AgentWorkflowResponse(
        ticket_id=
            ticket_id,

        action_id=
            action_id,

        status=
            "RESOLVED",

        assignee_id=
            ticket[
                "assignee_id"
            ],

        escalation_reason=None,

        resolution_code=
            resolution_code,
    )