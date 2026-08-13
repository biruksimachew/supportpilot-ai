from hashlib import sha256
from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.agent_workflow import (
    AgentSendReplyResponse,
)


class DeliveryTicketNotFoundError(
    LookupError
):
    pass


class DeliveryConflictError(
    RuntimeError
):
    pass


class DeliveryProviderUnavailableError(
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

def _checksum(
    body: str,
) -> str:

    return sha256(
        body.encode(
            "utf-8"
        )
    ).hexdigest()


def _load_latest_draft(
    cursor,
    *,
    ticket_id: UUID,
) -> dict | None:

    cursor.execute(
        """
        select
            id,

            after_value
                ->> 'ai_run_id'
                as ai_run_id,

            after_value
                ->> 'original_body'
                as original_body

        from public.agent_actions

        where ticket_id = %s

          and action =
              'AI_DRAFT_CAPTURED'

        order by
            created_at desc,
            id desc

        limit 1;
        """,
        (
            ticket_id,
        ),
    )

    return cursor.fetchone()


def _existing_delivery(
    cursor,
    *,
    ticket_id: UUID,
    idempotency_key: UUID,
) -> dict | None:

    cursor.execute(
        """
        select
            id,
            channel,
            body_checksum,
            status,
            response_message_id

        from public.outbound_deliveries

        where ticket_id = %s
          and idempotency_key = %s

        limit 1;
        """,
        (
            ticket_id,
            idempotency_key,
        ),
    )

    return cursor.fetchone()


def send_agent_reply(
    *,
    user: InternalUser,

    ticket_id: UUID,

    idempotency_key: UUID,

    body: str,
) -> AgentSendReplyResponse:

    normalized_body = (
        body.strip()
    )

    if not normalized_body:
        raise ValueError(
            "Reply cannot be empty."
        )


    body_checksum = (
        _checksum(
            normalized_body
        )
    )


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        id,
                        channel,
                        status,
                        customer_ref

                    from public.tickets

                    where id = %s

                    for update;
                    """,
                    (
                        ticket_id,
                    ),
                )


                ticket = (
                    cursor.fetchone()
                )


                if ticket is None:
                    raise (
                        DeliveryTicketNotFoundError(
                            "Ticket not found."
                        )
                    )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise (
                        DeliveryConflictError(
                            (
                                "Resolved tickets "
                                "cannot send replies."
                            )
                        )
                    )


                existing = (
                    _existing_delivery(
                        cursor,

                        ticket_id=
                            ticket_id,

                        idempotency_key=
                            idempotency_key,
                    )
                )


                if existing is not None:

                    if (
                        existing[
                            "body_checksum"
                        ]
                        != body_checksum
                    ):
                        raise (
                            DeliveryConflictError(
                                (
                                    "This idempotency "
                                    "key was already "
                                    "used with different "
                                    "reply content."
                                )
                            )
                        )


                    if (
                        existing[
                            "status"
                        ]
                        == "DELIVERED"
                    ):
                        return (
                            AgentSendReplyResponse(
                                ticket_id=
                                    ticket_id,

                                delivery_id=
                                    existing[
                                        "id"
                                    ],

                                message_id=
                                    existing[
                                        "response_message_id"
                                    ],

                                status=
                                    "DELIVERED",

                                ticket_status=
                                    ticket[
                                        "status"
                                    ],

                                channel=
                                    existing[
                                        "channel"
                                    ],

                                edited_from_ai_draft=
                                    False,

                                idempotent_replay=
                                    True,
                            )
                        )


                    raise (
                        DeliveryConflictError(
                            (
                                "A delivery with "
                                "this idempotency "
                                "key already exists "
                                "but is not confirmed "
                                "delivered."
                            )
                        )
                    )


                latest_draft = (
                    _load_latest_draft(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                original_body = (
                    latest_draft[
                        "original_body"
                    ]

                    if latest_draft
                    is not None

                    else None
                )


                edited = (
                    original_body
                    is not None

                    and original_body.strip()
                    != normalized_body
                )


                if (
                    ticket["channel"]
                    == "email"
                ):
                    raise (
                        DeliveryProviderUnavailableError(
                            (
                                "Outbound Gmail "
                                "delivery is not "
                                "configured yet."
                            )
                        )
                    )


                if (
                    ticket["channel"]
                    != "chat"
                ):
                    raise (
                        DeliveryProviderUnavailableError(
                            (
                                "Unsupported outbound "
                                "ticket channel."
                            )
                        )
                    )


                ai_run_id = (
                    latest_draft[
                        "ai_run_id"
                    ]

                    if latest_draft
                    is not None

                    else None
                )


                draft_action_id = (
                    latest_draft[
                        "id"
                    ]

                    if latest_draft
                    is not None

                    else None
                )


                cursor.execute(
                    """
                    insert into
                        public.outbound_deliveries (
                            ticket_id,
                            requested_by,

                            ai_run_id,
                            draft_action_id,

                            idempotency_key,

                            channel,
                            provider,

                            body,
                            body_checksum,

                            status,
                            attempt_count
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

                        %s,

                        'chat',
                        'supportpilot-chat',

                        %s,
                        %s,

                        'PENDING',
                        1
                    )

                    returning id;
                    """,
                    (
                        ticket_id,
                        user.id,

                        ai_run_id,
                        draft_action_id,

                        idempotency_key,

                        normalized_body,
                        body_checksum,
                    ),
                )


                delivery_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )


                external_message_id = (
                    "agent-chat:"
                    + str(
                        delivery_id
                    )
                )


                cursor.execute(
                    """
                    insert into public.messages (
                        ticket_id,

                        direction,
                        sender_type,

                        body,

                        external_message_id,

                        is_internal,

                        channel_metadata
                    )

                    values (
                        %s,

                        'outbound',
                        'agent',

                        %s,

                        %s,

                        false,

                        %s
                    )

                    returning id;
                    """,
                    (
                        ticket_id,

                        normalized_body,

                        external_message_id,

                        Jsonb(
                            {
                                "adapter":
                                    "agent_console",

                                "delivery_id":
                                    str(
                                        delivery_id
                                    ),

                                "idempotency_key":
                                    str(
                                        idempotency_key
                                    ),

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


                cursor.execute(
                    """
                    update public.outbound_deliveries

                    set
                        status =
                            'DELIVERED',

                        response_message_id =
                            %s,

                        provider_message_id =
                            %s,

                        delivered_at =
                            timezone(
                                'utc',
                                now()
                            ),

                        updated_at =
                            timezone(
                                'utc',
                                now()
                            )

                    where id = %s;
                    """,
                    (
                        message_id,

                        external_message_id,

                        delivery_id,
                    ),
                )


                cursor.execute(
                    """
                    update public.tickets

                    set
                        status =
                            'WAITING_CUSTOMER'

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


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

                        'AGENT_MESSAGE_SENT',

                        %s,
                        %s
                    );
                    """,
                    (
                        ticket_id,
                        user.id,

                        Jsonb(
                            {
                                "ticket_status":
                                    ticket[
                                        "status"
                                    ],

                                "draft_action_id":
                                    (
                                        str(
                                            draft_action_id
                                        )
                                        if draft_action_id
                                        else None
                                    ),
                            }
                        ),

                        Jsonb(
                            {
                                "delivery_id":
                                    str(
                                        delivery_id
                                    ),

                                "message_id":
                                    str(
                                        message_id
                                    ),

                                "ticket_status":
                                    "WAITING_CUSTOMER",

                                "edited_from_ai_draft":
                                    edited,
                            }
                        ),
                    ),
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
                        %s,
                        %s,

                        'OUTBOUND_MESSAGE_DELIVERED',

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

                        str(
                            ticket_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        ticket_id
                                    ),

                                "delivery_id":
                                    str(
                                        delivery_id
                                    ),

                                "message_id":
                                    str(
                                        message_id
                                    ),

                                "channel":
                                    "chat",

                                "provider":
                                    "supportpilot-chat",

                                "edited_from_ai_draft":
                                    edited,
                            }
                        ),
                    ),
                )


    return AgentSendReplyResponse(
        ticket_id=
            ticket_id,

        delivery_id=
            delivery_id,

        message_id=
            message_id,

        status=
            "DELIVERED",

        ticket_status=
            "WAITING_CUSTOMER",

        channel=
            "chat",

        edited_from_ai_draft=
            edited,

        idempotent_replay=
            False,
    )