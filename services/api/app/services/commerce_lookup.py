import re

from time import perf_counter
from uuid import UUID

from psycopg.rows import (
    dict_row,
)

from psycopg.types.json import (
    Jsonb,
)

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.commerce import (
    CommerceOrder,
    CommerceOrderLookupResponse,
)

from app.services.commerce import (
    CommerceProvider,
    CommerceProviderError,
)


ORDER_NUMBER_PATTERN = re.compile(
    r"^#NS[0-9]{5}$"
)


class CommerceCustomerNotFoundError(
    LookupError
):
    pass


class CommerceCustomerIdentityError(
    ValueError
):
    pass


class CommerceOrderFormatError(
    ValueError
):
    pass


class CommerceOrderNotFoundError(
    LookupError
):
    pass


class CommerceAIRunScopeError(
    ValueError
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


def _normalize_order_number(
    value: str,
) -> str:

    normalized = (
        value
        .strip()
        .upper()
    )


    if (
        normalized
        and not normalized.startswith(
            "#"
        )
    ):
        normalized = (
            "#"
            + normalized
        )


    if not ORDER_NUMBER_PATTERN.fullmatch(
        normalized
    ):
        raise CommerceOrderFormatError(
            (
                "Order number must match "
                "the Northstar format "
                "#NS10041."
            )
        )


    return normalized


def _load_customer(
    *,
    customer_id: UUID,
) -> dict:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    id,
                    external_id

                from public.customers

                where id = %s

                limit 1;
                """,
                (
                    customer_id,
                ),
            )


            customer = (
                cursor.fetchone()
            )


    if customer is None:

        raise CommerceCustomerNotFoundError(
            "Customer not found."
        )


    external_id = (
        customer[
            "external_id"
        ]
    )


    if (
        external_id is None
        or not external_id.strip()
    ):

        raise CommerceCustomerIdentityError(
            (
                "Customer does not have "
                "a commerce identity."
            )
        )


    return customer


def _load_ai_run_scope(
    *,
    ai_run_id: UUID,
) -> dict:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    ar.id,
                    ar.ticket_id,
                    t.customer_ref

                from public.ai_runs ar

                join public.tickets t
                    on t.id =
                        ar.ticket_id

                where ar.id = %s

                limit 1;
                """,
                (
                    ai_run_id,
                ),
            )


            row = (
                cursor.fetchone()
            )


    if row is None:

        raise CommerceAIRunScopeError(
            "AI run was not found."
        )


    return row


def _insert_tool_call(
    cursor,
    *,
    ai_run_id: UUID,

    safe_request_summary: str,

    result_summary: str,

    status: str,

    latency_ms: int,
) -> UUID:

    cursor.execute(
        """
        insert into public.tool_calls (
            ai_run_id,
            tool_name,

            safe_request_summary,
            result_summary,

            status,
            latency_ms
        )

        values (
            %s,
            'commerce.lookup_order',

            %s,
            %s,

            %s,
            %s
        )

        returning id;
        """,
        (
            ai_run_id,

            safe_request_summary,
            result_summary,

            status,
            latency_ms,
        ),
    )


    return cursor.fetchone()[
        "id"
    ]


def _insert_audit_event(
    cursor,
    *,
    user: InternalUser,

    customer_id: UUID,
    order_number: str,

    outcome: str,

    ai_run_id:
        UUID | None,

    tool_call_id:
        UUID | None,
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

            'COMMERCE_ORDER_LOOKUP',

            'commerce_order',
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

            order_number,

            Jsonb(
                {
                    "customer_ref":
                        str(
                            customer_id
                        ),

                    "outcome":
                        outcome,

                    "ai_run_id":
                        (
                            str(
                                ai_run_id
                            )
                            if ai_run_id
                            else None
                        ),

                    "tool_call_id":
                        (
                            str(
                                tool_call_id
                            )
                            if tool_call_id
                            else None
                        ),
                }
            ),
        ),
    )


def _safe_request_summary(
    *,
    customer_id: UUID,
    order_number: str,
) -> str:

    return (
        "customer-scoped order lookup; "
        f"customer_ref={customer_id}; "
        f"order_number={order_number}"
    )


def _result_summary(
    order: CommerceOrder,
) -> str:

    return (
        f"status={order.status}; "
        f"item_count={len(order.items)}; "
        "tracking_present="
        + (
            "true"
            if order.tracking_number
            else "false"
        )
    )


def _record_non_success(
    *,
    user: InternalUser,

    customer_id: UUID,
    order_number: str,

    ai_run_id:
        UUID | None,

    status: str,

    result_summary: str,

    latency_ms: int,
) -> None:

    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                tool_call_id = None


                if ai_run_id is not None:

                    tool_call_id = (
                        _insert_tool_call(
                            cursor,

                            ai_run_id=
                                ai_run_id,

                            safe_request_summary=
                                _safe_request_summary(
                                    customer_id=
                                        customer_id,

                                    order_number=
                                        order_number,
                                ),

                            result_summary=
                                result_summary,

                            status=
                                status,

                            latency_ms=
                                latency_ms,
                        )
                    )


                _insert_audit_event(
                    cursor,

                    user=
                        user,

                    customer_id=
                        customer_id,

                    order_number=
                        order_number,

                    outcome=
                        status,

                    ai_run_id=
                        ai_run_id,

                    tool_call_id=
                        tool_call_id,
                )


def lookup_customer_order(
    *,
    user: InternalUser,

    customer_id: UUID,
    order_number: str,

    provider: CommerceProvider,

    ai_run_id:
        UUID | None = None,

) -> CommerceOrderLookupResponse:

    normalized_order_number = (
        _normalize_order_number(
            order_number
        )
    )


    customer = _load_customer(
        customer_id=
            customer_id
    )


    customer_external_id = (
        customer[
            "external_id"
        ]
    )


    if ai_run_id is not None:

        ai_scope = (
            _load_ai_run_scope(
                ai_run_id=
                    ai_run_id
            )
        )


        if (
            ai_scope[
                "customer_ref"
            ]
            != customer_id
        ):

            _record_non_success(
                user=
                    user,

                customer_id=
                    customer_id,

                order_number=
                    normalized_order_number,

                ai_run_id=
                    ai_run_id,

                status=
                    "BLOCKED",

                result_summary=
                    (
                        "AI run customer scope "
                        "does not match requested "
                        "customer."
                    ),

                latency_ms=
                    0,
            )


            raise CommerceAIRunScopeError(
                (
                    "AI run customer scope "
                    "does not match the "
                    "requested customer."
                )
            )


    started_at = (
        perf_counter()
    )


    try:

        order = provider.lookup_order(
            customer_external_id=
                customer_external_id,

            order_number=
                normalized_order_number,
        )


    except CommerceProviderError:

        latency_ms = max(
            0,

            round(
                (
                    perf_counter()
                    - started_at
                )
                * 1000
            ),
        )


        _record_non_success(
            user=
                user,

            customer_id=
                customer_id,

            order_number=
                normalized_order_number,

            ai_run_id=
                ai_run_id,

            status=
                "FAILED",

            result_summary=
                (
                    "Commerce provider "
                    "request failed."
                ),

            latency_ms=
                latency_ms,
        )


        raise


    latency_ms = max(
        0,

        round(
            (
                perf_counter()
                - started_at
            )
            * 1000
        ),
    )


    if order is None:

        _record_non_success(
            user=
                user,

            customer_id=
                customer_id,

            order_number=
                normalized_order_number,

            ai_run_id=
                ai_run_id,

            status=
                "BLOCKED",

            result_summary=
                (
                    "Order not available "
                    "within customer scope."
                ),

            latency_ms=
                latency_ms,
        )


        raise CommerceOrderNotFoundError(
            (
                "Order was not found "
                "for this customer."
            )
        )


    fulfillment_summary = {
        "items": [
            item.model_dump(
                mode="json"
            )
            for item
            in order.items
        ],

        "tracking_number":
            order.tracking_number,

        "delivered_at":
            (
                order.delivered_at
                .isoformat()

                if order.delivered_at
                else None
            ),
    }


    total_summary = {
        "total":
            order.total,

        "currency":
            order.currency,
    }


    with get_database_connection() as connection:

        connection.row_factory = (
            dict_row
        )


        with connection.transaction():

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    insert into public.orders_cache (
                        external_order_id,
                        customer_ref,

                        status,

                        fulfillment_summary,
                        total_summary,

                        retrieved_at
                    )

                    values (
                        %s,
                        %s,

                        %s,

                        %s,
                        %s,

                        now()
                    )

                    on conflict (
                        external_order_id
                    )

                    do update set
                        customer_ref =
                            excluded.customer_ref,

                        status =
                            excluded.status,

                        fulfillment_summary =
                            excluded.fulfillment_summary,

                        total_summary =
                            excluded.total_summary,

                        retrieved_at =
                            excluded.retrieved_at

                    returning retrieved_at;
                    """,
                    (
                        order.order_number,
                        customer_id,

                        order.status,

                        Jsonb(
                            fulfillment_summary
                        ),

                        Jsonb(
                            total_summary
                        ),
                    ),
                )


                cached_at = (
                    cursor.fetchone()[
                        "retrieved_at"
                    ]
                )


                tool_call_id = None


                if ai_run_id is not None:

                    tool_call_id = (
                        _insert_tool_call(
                            cursor,

                            ai_run_id=
                                ai_run_id,

                            safe_request_summary=
                                _safe_request_summary(
                                    customer_id=
                                        customer_id,

                                    order_number=
                                        normalized_order_number,
                                ),

                            result_summary=
                                _result_summary(
                                    order
                                ),

                            status=
                                "SUCCEEDED",

                            latency_ms=
                                latency_ms,
                        )
                    )


                _insert_audit_event(
                    cursor,

                    user=
                        user,

                    customer_id=
                        customer_id,

                    order_number=
                        normalized_order_number,

                    outcome=
                        "SUCCEEDED",

                    ai_run_id=
                        ai_run_id,

                    tool_call_id=
                        tool_call_id,
                )


    return CommerceOrderLookupResponse(
        customer_id=
            customer_id,

        order=
            order,

        cached_at=
            cached_at,

        tool_call_id=
            tool_call_id,
    )