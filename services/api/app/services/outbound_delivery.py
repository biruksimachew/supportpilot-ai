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

from app.services.email_outbound import (
    EmailOutboundConfigurationError,
    EmailOutboundConfirmedFailure,
    EmailOutboundUncertainError,
    deliver_email_via_n8n,
    validate_email_outbound_configuration,
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


class DeliveryConfirmedFailureError(
    RuntimeError
):
    pass


class DeliveryUncertainError(
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


def _gmail_provider_id(
    value: str | None,
) -> str:

    normalized = str(
        value or ""
    ).strip()

    prefix = "gmail:"

    if normalized.lower().startswith(
        prefix
    ):
        return normalized[
            len(prefix):
        ].strip()

    return normalized
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

            body,
            body_checksum,

            status,
            attempt_count,

            draft_action_id,
            ai_run_id,

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


def _load_ticket(
    cursor,
    *,
    ticket_id: UUID,
) -> dict:

    cursor.execute(
        """
        select
            t.id,
            t.channel,
            t.status,
            t.customer_ref,

            t.external_thread_id,

            c.email
                as customer_email,

            latest_inbound.external_message_id
                as reply_message_id,

            latest_inbound.subject
                as inbound_subject,

            latest_inbound.customer_hint
                as inbound_customer_hint

        from public.tickets as t

        left join public.customers as c
            on c.id =
                t.customer_ref

        left join lateral (
            select
                m.external_message_id,
                m.subject,
                m.customer_hint

            from public.messages as m

            where
                m.ticket_id = t.id

                and m.direction =
                    'inbound'

            order by
                m.received_at desc,
                m.created_at desc,
                m.id desc

            limit 1
        ) as latest_inbound
            on true

        where t.id = %s

        for update
            of t;
        """,
        (
            ticket_id,
        ),
    )

    ticket = cursor.fetchone()

    if ticket is None:
        raise DeliveryTicketNotFoundError(
            "Ticket not found."
        )

    return ticket


def _edited_from_draft(
    *,
    latest_draft: dict | None,

    body: str,
) -> bool:

    if latest_draft is None:
        return False

    original_body = (
        latest_draft[
            "original_body"
        ]
    )

    if original_body is None:
        return False

    return (
        original_body.strip()
        != body
    )


def _insert_success_action_and_audit(
    cursor,
    *,
    user: InternalUser,

    ticket_id: UUID,

    previous_status: str,

    delivery_id: UUID,

    message_id: UUID,

    draft_action_id:
        UUID | None,

    channel: str,

    provider: str,

    edited: bool,
) -> None:

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
                        previous_status,

                    "draft_action_id":
                        (
                            str(
                                draft_action_id
                            )
                            if draft_action_id
                            is not None

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

                    "channel":
                        channel,

                    "provider":
                        provider,
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
                        channel,

                    "provider":
                        provider,

                    "edited_from_ai_draft":
                        edited,
                }
            ),
        ),
    )


def _send_chat_reply(
    *,
    cursor,

    user: InternalUser,

    ticket: dict,

    idempotency_key: UUID,

    normalized_body: str,

    body_checksum: str,

    latest_draft: dict | None,

    edited: bool,
) -> AgentSendReplyResponse:

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
            ticket[
                "id"
            ],

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
            ticket[
                "id"
            ],

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

        set status =
            'WAITING_CUSTOMER'

        where id = %s;
        """,
        (
            ticket[
                "id"
            ],
        ),
    )


    _insert_success_action_and_audit(
        cursor,

        user=user,

        ticket_id=
            ticket[
                "id"
            ],

        previous_status=
            ticket[
                "status"
            ],

        delivery_id=
            delivery_id,

        message_id=
            message_id,

        draft_action_id=
            draft_action_id,

        channel=
            "chat",

        provider=
            "supportpilot-chat",

        edited=
            edited,
    )


    return AgentSendReplyResponse(
        ticket_id=
            ticket[
                "id"
            ],

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


def _mark_email_outcome(
    *,
    user: InternalUser,

    ticket_id: UUID,

    delivery_id: UUID,

    status: str,

    error_code: str,

    error_summary: str,
) -> None:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    update public.outbound_deliveries

                    set
                        status =
                            %s,

                        error_code =
                            %s,

                        error_summary =
                            %s,

                        updated_at =
                            timezone(
                                'utc',
                                now()
                            )

                    where id = %s;
                    """,
                    (
                        status,

                        error_code,

                        error_summary[
                            :1000
                        ],

                        delivery_id,
                    ),
                )


                action = (
                    "AGENT_MESSAGE_DELIVERY_"
                    + status
                )


                cursor.execute(
                    """
                    insert into public.agent_actions (
                        ticket_id,
                        user_id,

                        action,

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

                        %s
                    );
                    """,
                    (
                        ticket_id,

                        user.id,

                        action,

                        Jsonb(
                            {
                                "delivery_id":
                                    str(
                                        delivery_id
                                    ),

                                "delivery_status":
                                    status,

                                "error_code":
                                    error_code,
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

                        (
                            "OUTBOUND_MESSAGE_"
                            + status
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

                                "channel":
                                    "email",

                                "provider":
                                    "gmail",

                                "error_code":
                                    error_code,
                            }
                        ),
                    ),
                )


def _finalize_email_delivery(
    *,
    user: InternalUser,

    ticket_id: UUID,

    delivery_id: UUID,

    normalized_body: str,

    destination: str,

    subject: str | None,

    provider_message_id: str,

    provider_thread_id:
        str | None,

    edited: bool,
) -> AgentSendReplyResponse:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        od.status,
                        od.draft_action_id,

                        t.status
                            as ticket_status

                    from public.outbound_deliveries
                        as od

                    join public.tickets as t
                        on t.id =
                            od.ticket_id

                    where
                        od.id = %s

                        and od.ticket_id = %s

                    for update
                        of od,
                           t;
                    """,
                    (
                        delivery_id,
                        ticket_id,
                    ),
                )


                row = cursor.fetchone()


                if row is None:
                    raise DeliveryConflictError(
                        (
                            "Outbound delivery "
                            "state was not found."
                        )
                    )


                if (
                    row["status"]
                    == "DELIVERED"
                ):
                    raise DeliveryConflictError(
                        (
                            "Outbound delivery "
                            "was already finalized."
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

                        subject,
                        customer_hint,

                        channel_metadata
                    )

                    values (
                        %s,

                        'outbound',
                        'agent',

                        %s,

                        %s,

                        false,

                        %s,
                        %s,

                        %s
                    )

                    returning id;
                    """,
                    (
                        ticket_id,

                        normalized_body,

                        provider_message_id,

                        subject,
                        destination,

                        Jsonb(
                            {
                                "adapter":
                                    "n8n_gmail",

                                "delivery_id":
                                    str(
                                        delivery_id
                                    ),

                                "gmail_thread_id":
                                    provider_thread_id,

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

                        error_code =
                            null,

                        error_summary =
                            null,

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

                        provider_message_id,

                        delivery_id,
                    ),
                )


                cursor.execute(
                    """
                    update public.tickets

                    set status =
                        'WAITING_CUSTOMER'

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                _insert_success_action_and_audit(
                    cursor,

                    user=user,

                    ticket_id=
                        ticket_id,

                    previous_status=
                        row[
                            "ticket_status"
                        ],

                    delivery_id=
                        delivery_id,

                    message_id=
                        message_id,

                    draft_action_id=
                        row[
                            "draft_action_id"
                        ],

                    channel=
                        "email",

                    provider=
                        "gmail",

                    edited=
                        edited,
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
            "email",

        edited_from_ai_draft=
            edited,

        idempotent_replay=
            False,
    )


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


    # Email delivery is intentionally two-phase:
    #
    # 1. persist PENDING
    # 2. commit
    # 3. call n8n/Gmail
    # 4. persist final outcome
    #
    # We never hold a database transaction open
    # during a network request.

    email_context: dict | None = None


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                ticket = (
                    _load_ticket(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                if (
                    ticket["status"]
                    == "RESOLVED"
                ):
                    raise DeliveryConflictError(
                        (
                            "Resolved tickets "
                            "cannot send replies."
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
                        raise DeliveryConflictError(
                            (
                                "This idempotency "
                                "key was already "
                                "used with different "
                                "reply content."
                            )
                        )


                    if (
                        existing[
                            "status"
                        ]
                        == "DELIVERED"
                    ):

                        return AgentSendReplyResponse(
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


                    if (
                        existing[
                            "status"
                        ]
                        in {
                            "PENDING",
                            "UNCERTAIN",
                        }
                    ):
                        raise DeliveryConflictError(
                            (
                                "Delivery outcome "
                                "is not safe to retry "
                                "automatically."
                            )
                        )


                    # Confirmed FAILED email attempts may be
                    # retried with the SAME idempotency key.
                    if (
                        existing[
                            "status"
                        ]
                        == "FAILED"
                    ):

                        if (
                            ticket[
                                "channel"
                            ]
                            != "email"
                        ):
                            raise DeliveryConflictError(
                                (
                                    "Failed delivery "
                                    "cannot be retried "
                                    "for this channel."
                                )
                            )

                        cursor.execute(
                            """
                            update public.outbound_deliveries

                            set
                                status =
                                    'PENDING',

                                attempt_count =
                                    attempt_count + 1,

                                error_code =
                                    null,

                                error_summary =
                                    null,

                                updated_at =
                                    timezone(
                                        'utc',
                                        now()
                                    )

                            where id = %s;
                            """,
                            (
                                existing[
                                    "id"
                                ],
                            ),
                        )


                        delivery_id = (
                            existing[
                                "id"
                            ]
                        )


                    else:
                        raise DeliveryConflictError(
                            (
                                "Unsupported existing "
                                "delivery state."
                            )
                        )


                latest_draft = (
                    _load_latest_draft(
                        cursor,

                        ticket_id=
                            ticket_id,
                    )
                )


                edited = (
                    _edited_from_draft(
                        latest_draft=
                            latest_draft,

                        body=
                            normalized_body,
                    )
                )


                if (
                    ticket["channel"]
                    == "chat"
                ):

                    if existing is not None:
                        raise DeliveryConflictError(
                            (
                                "Chat delivery "
                                "cannot enter a "
                                "retry state."
                            )
                        )


                    return _send_chat_reply(
                        cursor=cursor,

                        user=user,

                        ticket=ticket,

                        idempotency_key=
                            idempotency_key,

                        normalized_body=
                            normalized_body,

                        body_checksum=
                            body_checksum,

                        latest_draft=
                            latest_draft,

                        edited=
                            edited,
                    )


                if (
                    ticket["channel"]
                    != "email"
                ):
                    raise DeliveryProviderUnavailableError(
                        (
                            "Unsupported outbound "
                            "ticket channel."
                        )
                    )


                try:
                    validate_email_outbound_configuration()

                except EmailOutboundConfigurationError as exc:
                    raise DeliveryProviderUnavailableError(
                        (
                            "Outbound Gmail delivery "
                            "is not configured."
                        )
                    ) from exc


                thread_id = (
                    _gmail_provider_id(
                        ticket[
                            "external_thread_id"
                        ]
                    )
                )


                reply_message_id = (
                    _gmail_provider_id(
                        ticket[
                            "reply_message_id"
                        ]
                    )
                )


                destination = str(
                    ticket[
                        "customer_email"
                    ]
                    or
                    ticket[
                        "inbound_customer_hint"
                    ]
                    or ""
                ).strip()


                if (
                    not thread_id
                    or not reply_message_id
                    or not destination
                ):
                    raise DeliveryConflictError(
                        (
                            "Email reply context "
                            "is incomplete."
                        )
                    )


                if existing is None:

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

                                destination,
                                subject,

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

                            'email',
                            'gmail',

                            %s,
                            %s,

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

                            destination,
                            ticket[
                                "inbound_subject"
                            ],

                            normalized_body,
                            body_checksum,
                        ),
                    )


                    delivery_id = (
                        cursor.fetchone()[
                            "id"
                        ]
                    )


                email_context = {
                    "delivery_id":
                        delivery_id,

                    "thread_id":
                        thread_id,

                    "message_id":
                        reply_message_id,

                    "destination":
                        destination,

                    "subject":
                        ticket[
                            "inbound_subject"
                        ],

                    "edited":
                        edited,
                }


    assert email_context is not None


    try:

        provider_result = (
            deliver_email_via_n8n(
                delivery_id=
                    email_context[
                        "delivery_id"
                    ],

                idempotency_key=
                    idempotency_key,

                thread_id=
                    email_context[
                        "thread_id"
                    ],

                message_id=
                    email_context[
                        "message_id"
                    ],

                destination=
                    email_context[
                        "destination"
                    ],

                subject=
                    email_context[
                        "subject"
                    ],

                body=
                    normalized_body,
            )
        )


    except EmailOutboundConfirmedFailure as exc:

        _mark_email_outcome(
            user=user,

            ticket_id=
                ticket_id,

            delivery_id=
                email_context[
                    "delivery_id"
                ],

            status=
                "FAILED",

            error_code=
                "GMAIL_REPLY_FAILED",

            error_summary=
                str(exc),
        )


        raise DeliveryConfirmedFailureError(
            (
                "Gmail explicitly rejected "
                "the outbound reply."
            )
        ) from exc


    except EmailOutboundUncertainError as exc:

        _mark_email_outcome(
            user=user,

            ticket_id=
                ticket_id,

            delivery_id=
                email_context[
                    "delivery_id"
                ],

            status=
                "UNCERTAIN",

            error_code=
                "GMAIL_DELIVERY_UNCERTAIN",

            error_summary=
                str(exc),
        )


        raise DeliveryUncertainError(
            (
                "Email delivery could not "
                "be confirmed. Do not retry "
                "blindly."
            )
        ) from exc


    return _finalize_email_delivery(
        user=user,

        ticket_id=
            ticket_id,

        delivery_id=
            email_context[
                "delivery_id"
            ],

        normalized_body=
            normalized_body,

        destination=
            email_context[
                "destination"
            ],

        subject=
            email_context[
                "subject"
            ],

        provider_message_id=
            provider_result
            .provider_message_id,

        provider_thread_id=
            provider_result
            .provider_thread_id,

        edited=
            email_context[
                "edited"
            ],
    )