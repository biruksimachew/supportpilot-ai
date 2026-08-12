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
    "88888888-8888-4888-8888-888888888888"
)


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m4b-manager@test.local",

        name=
            "M4B Test Manager",

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


def create_ticket(
    *,
    message: str,
    customer_hint: str,
) -> tuple[str, str]:

    response = client.post(
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
                customer_hint,

            "subject":
                None,

            "body":
                message,

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


    assert response.status_code == 201


    payload = response.json()


    return (
        payload[
            "ticket_id"
        ],

        payload[
            "message_id"
        ],
    )


def create_ai_run(
    *,
    ticket_id: str,
    message_id: str,
) -> str:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

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
                    'verification-test-v1',
                    'm4b-test',

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


            return str(
                cursor.fetchone()[
                    0
                ]
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

                where entity_type = 'ticket'
                  and entity_id = %s;
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


def test_verified_identity_allows_ai_scoped_order_lookup():

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    ticket_id = None


    try:

        ticket_id, message_id = (
            create_ticket(
                message=
                    (
                        "Where is order "
                        "#NS10041?"
                    ),

                customer_hint=
                    "unverified@example.com",
            )
        )


        verification = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/identity/verify"
            ),

            json={
                "email":
                    "amina.demo@example.com",

                "postcode":
                    "10001",

                "order_number":
                    "#NS10041",
            },
        )


        assert verification.status_code == 200


        verified = verification.json()


        assert verified[
            "verified"
        ] is True

        assert verified[
            "verification_status"
        ] == "VERIFIED"

        assert verified[
            "verified_order_number"
        ] == "#NS10041"

        assert verified[
            "verification_method"
        ] == "EMAIL_POSTCODE_ORDER"


        amina_id = (
            load_customer_id(
                "CUST-1001"
            )
        )


        assert verified[
            "customer_id"
        ] == amina_id


        ai_run_id = create_ai_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,
        )


        lookup = client.post(
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


        assert lookup.status_code == 200


        order = lookup.json()[
            "order"
        ]


        assert order[
            "status"
        ] == "IN_TRANSIT"

        assert order[
            "tracking_number"
        ] == "TRK-DEMO-10041"


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        identity_verification_status,
                        identity_verification_method,
                        identity_verified_order_number,
                        identity_verification_attempts

                    from public.tickets

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                row = cursor.fetchone()


                assert row == (
                    "VERIFIED",
                    "EMAIL_POSTCODE_ORDER",
                    "#NS10041",
                    1,
                )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )


def test_identity_mismatch_blocks_order_disclosure():

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    ticket_id = None


    try:

        ticket_id, message_id = (
            create_ticket(
                message=
                    (
                        "My order is #NS10043, "
                        "email is "
                        "someone.else@example.com."
                    ),

                customer_hint=
                    "someone.else@example.com",
            )
        )


        verification = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/identity/verify"
            ),

            json={
                "email":
                    "someone.else@example.com",

                "postcode":
                    "10003",

                "order_number":
                    "#NS10043",
            },
        )


        assert verification.status_code == 200


        result = verification.json()


        assert result[
            "verified"
        ] is False

        assert result[
            "verification_status"
        ] == "FAILED"

        assert result[
            "customer_id"
        ] is None

        assert result[
            "verified_order_number"
        ] is None


        maya_id = (
            load_customer_id(
                "CUST-1003"
            )
        )


        ai_run_id = create_ai_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,
        )


        lookup = client.post(
            "/api/v1/agent/commerce/orders/lookup",

            json={
                "customer_id":
                    maya_id,

                "order_number":
                    "#NS10043",

                "ai_run_id":
                    ai_run_id,
            },
        )


        assert lookup.status_code == 409


        body = str(
            lookup.json()
        )


        assert (
            "PARTIALLY_FULFILLED"
            not in body
        )

        assert (
            "CampGlow"
            not in body
        )

        assert (
            "Packing Cube"
            not in body
        )

        assert (
            "101"
            not in body
        )


        assert (
            lookup.json()[
                "detail"
            ][
                "code"
            ]
            == "CUSTOMER_NOT_VERIFIED"
        )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )


def test_valid_other_customer_cannot_verify_someone_elses_order():

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    ticket_id = None


    try:

        ticket_id, _ = (
            create_ticket(
                message=
                    (
                        "Where is order "
                        "#NS10041?"
                    ),

                customer_hint=
                    "daniel.demo@example.com",
            )
        )


        verification = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/identity/verify"
            ),

            json={
                "email":
                    "daniel.demo@example.com",

                "postcode":
                    "10002",

                "order_number":
                    "#NS10041",
            },
        )


        assert verification.status_code == 200


        result = verification.json()


        assert result[
            "verified"
        ] is False

        assert result[
            "verification_status"
        ] == "FAILED"

        assert result[
            "customer_id"
        ] is None


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )