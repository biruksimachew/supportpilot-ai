from datetime import (
    datetime,
    timezone,
)

from uuid import (
    UUID,
    uuid4,
)

import psycopg

from fastapi.testclient import (
    TestClient,
)

from app.core.auth import (
    get_current_internal_user,
)

from app.core.config import (
    settings,
)

from app.main import app

from app.schemas.auth import (
    InternalUser,
)


client = TestClient(app)


MANAGER_ID = UUID(
    "77777777-7777-4777-8777-777777777777"
)


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m4a-manager@test.local",

        name=
            "M4A Test Manager",

        role=
            "SUPPORT_MANAGER",
    )


def load_customer_id(
    external_id: str,
) -> str:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select id
                from public.customers
                where external_id = %s;
                """,
                (
                    external_id,
                ),
            )


            row = cursor.fetchone()


    assert row is not None

    return str(
        row[0]
    )


def cleanup_ticket(
    ticket_id: str,
) -> None:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                delete
                from public.audit_events

                where metadata ->> 'ai_run_id'
                in (
                    select id::text
                    from public.ai_runs
                    where ticket_id = %s
                );
                """,
                (
                    ticket_id,
                ),
            )

            cursor.execute(
                """
                delete
                from public.audit_events

                where metadata ->> 'ticket_id'
                    = %s;
                """,
                (
                    ticket_id,
                ),
            )

            cursor.execute(
                """
                delete
                from public.tickets
                where id = %s;
                """,
                (
                    ticket_id,
                ),
            )

def test_customer_scoped_order_lookup_and_tool_audit():

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    ticket_id = None


    try:

        amina_id = (
            load_customer_id(
                "CUST-1001"
            )
        )

        daniel_id = (
            load_customer_id(
                "CUST-1002"
            )
        )


        intake_response = client.post(
            "/api/v1/intake/messages",

            json={
                "channel":
                    "chat",

                "external_message_id":
                    str(
                        uuid4()
                    ),

                "external_thread_id":
                    str(
                        uuid4()
                    ),

                "customer_hint":
                    "amina.demo@example.com",

                "subject":
                    None,

                "body":
                    (
                        "Where is order "
                        "#NS10041?"
                    ),

                "received_at":
                    datetime.now(
                        timezone.utc
                    ).isoformat(),

                "attachments":
                    [],

                "metadata": {
                    "test":
                        True,
                },
            },
        )


        assert (
            intake_response.status_code
            == 201
        )


        intake = (
            intake_response.json()
        )


        ticket_id = (
            intake[
                "ticket_id"
            ]
        )

        message_id = (
            intake[
                "message_id"
            ]
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                # --------------------------------------------------
                # This is an M4A commerce-isolation test.
                #
                # Identity verification itself is tested separately
                # in test_identity_verification.py.
                #
                # Therefore, for this older M4A test, we establish a
                # legitimate VERIFIED ticket directly in the fixture.
                # --------------------------------------------------

                cursor.execute(
                    """
                    update public.tickets

                    set
                        customer_ref = %s,

                        identity_verification_status =
                            'VERIFIED',

                        identity_verification_method =
                            'EMAIL_POSTCODE_ORDER',

                        identity_verified_at =
                            now(),

                        identity_verified_order_number =
                            '#NS10041',

                        identity_verification_attempts =
                            1

                    where id = %s;
                    """,
                    (
                        amina_id,
                        ticket_id,
                    ),
                )


                cursor.execute(
                    """
                    insert into public.ai_runs (
                        ticket_id,
                        message_id,

                        provider,
                        model,
                        prompt_version,

                        decision,
                        decision_reasons
                    )

                    values (
                        %s,
                        %s,

                        'test',
                        'commerce-test-v1',
                        'm4a-test',

                        'REVIEW_REQUIRED',
                        '[]'::jsonb
                    )

                    returning id;
                    """,
                    (
                        ticket_id,
                        message_id,
                    ),
                )


                ai_run_id = str(
                    cursor.fetchone()[
                        0
                    ]
                )

        valid = client.post(
            "/api/v1/agent/commerce/orders/lookup",

            json={
                "customer_id":
                    amina_id,

                "order_number":
                    "#NS10041",

                "ai_run_id":
                    ai_run_id,
            },
        )


        assert (
            valid.status_code
            == 200
        )


        result = (
            valid.json()
        )


        assert (
            result[
                "order"
            ][
                "order_number"
            ]
            == "#NS10041"
        )


        assert (
            result[
                "order"
            ][
                "customer_id"
            ]
            == "CUST-1001"
        )


        assert (
            result[
                "order"
            ][
                "status"
            ]
            == "IN_TRANSIT"
        )


        assert (
            result[
                "order"
            ][
                "tracking_number"
            ]
            == "TRK-DEMO-10041"
        )


        assert (
            result[
                "tool_call_id"
            ]
            is not None
        )


        # --------------------------------------------------
        # Same AI run cannot escape into another customer.
        # --------------------------------------------------

        scope_violation = client.post(
            "/api/v1/agent/commerce/orders/lookup",

            json={
                "customer_id":
                    daniel_id,

                "order_number":
                    "#NS10041",

                "ai_run_id":
                    ai_run_id,
            },
        )


        assert (
            scope_violation.status_code
            == 409
        )


        assert (
            "#NS10041"
            not in str(
                scope_violation.json()
            )
        )


        # --------------------------------------------------
        # Even without ai_run context, customer-scoped
        # provider lookup must not reveal another customer's
        # order.
        # --------------------------------------------------

        wrong_customer = client.post(
            "/api/v1/agent/commerce/orders/lookup",

            json={
                "customer_id":
                    daniel_id,

                "order_number":
                    "#NS10041",
            },
        )


        assert (
            wrong_customer.status_code
            == 404
        )


        body = str(
            wrong_customer.json()
        )


        assert (
            "IN_TRANSIT"
            not in body
        )

        assert (
            "TRK-DEMO-10041"
            not in body
        )

        assert (
            "89"
            not in body
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        customer_ref,
                        status,
                        fulfillment_summary,
                        total_summary

                    from public.orders_cache

                    where external_order_id =
                        '#NS10041';
                    """
                )


                cache_row = (
                    cursor.fetchone()
                )


                assert (
                    str(
                        cache_row[0]
                    )
                    == amina_id
                )

                assert (
                    cache_row[1]
                    == "IN_TRANSIT"
                )


                cursor.execute(
                    """
                    select
                        status,
                        tool_name

                    from public.tool_calls

                    where ai_run_id = %s

                    order by created_at;
                    """,
                    (
                        ai_run_id,
                    ),
                )


                tool_calls = (
                    cursor.fetchall()
                )


                assert (
                    tool_calls
                    == [
                        (
                            "SUCCEEDED",
                            "commerce.lookup_order",
                        ),
                        (
                            "BLOCKED",
                            "commerce.lookup_order",
                        ),
                    ]
                )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )

