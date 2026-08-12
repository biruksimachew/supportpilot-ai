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
    "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
)


class NeverCalledEmbeddingProvider:

    provider_name = "must-not-run"
    model = "must-not-run"
    dimensions = 1536


    def embed_query(
        self,
        text: str,
    ):

        raise AssertionError(
            (
                "Embedding provider should not "
                "run for order-status commerce."
            )
        )


    def embed(
        self,
        texts,
    ):

        raise AssertionError(
            (
                "Embedding provider should not "
                "run for order-status commerce."
            )
        )


class NeverCalledGenerationProvider:

    provider_name = "must-not-run"
    model = "must-not-run"


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):

        raise AssertionError(
            (
                "Generation provider should not "
                "run for order-status commerce."
            )
        )


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m4d-manager@test.local",

        name=
            "M4D Test Manager",

        role=
            "SUPPORT_MANAGER",
    )


def create_ticket(
    *,
    body: str,
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
                body,

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

                where metadata ->> 'ticket_id' = %s

                   or (
                        entity_type = 'ticket'
                        and entity_id = %s
                   );
                """,
                (
                    ticket_id,
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


def install_dependencies(
    monkeypatch,
) -> None:

    embedding_provider = (
        NeverCalledEmbeddingProvider()
    )

    generation_provider = (
        NeverCalledGenerationProvider()
    )


    monkeypatch.setattr(
        (
            "app.api.routes.support_ai."
            "get_embedding_provider"
        ),

        lambda:
            embedding_provider,
    )


    monkeypatch.setattr(
        (
            "app.api.routes.support_ai."
            "get_generation_provider"
        ),

        lambda:
            generation_provider,
    )


    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


def test_unverified_order_status_requests_clarification(
    monkeypatch,
):

    install_dependencies(
        monkeypatch
    )


    ticket_id = None


    try:

        ticket_id, message_id = (
            create_ticket(
                body=
                    (
                        "Where is order "
                        "#NS10041?"
                    ),

                customer_hint=
                    "amina.demo@example.com",
            )
        )


        response = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/messages/"
                + message_id
                + "/ai-draft"
            )
        )


        assert response.status_code == 200


        result = response.json()


        assert (
            result[
                "intent"
            ]
            == "order_status"
        )

        assert (
            result[
                "commerce_required"
            ]
            is True
        )

        assert (
            result[
                "order_number"
            ]
            == "#NS10041"
        )

        assert (
            result[
                "decision"
            ]
            == "REQUEST_CLARIFICATION"
        )

        assert (
            result[
                "safe_draft_ready"
            ]
            is False
        )

        assert (
            result[
                "generation_attempted"
            ]
            is False
        )

        assert (
            result[
                "commerce_order"
            ]
            is None
        )


        body = result[
            "answer"
        ][
            "answer"
        ]


        assert (
            "IN_TRANSIT"
            not in body
        )

        assert (
            "TRK-DEMO-10041"
            not in body
        )


        ai_run_id = (
            result[
                "ai_run_id"
            ]
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select count(*)::int

                    from public.tool_calls

                    where ai_run_id = %s;
                    """,
                    (
                        ai_run_id,
                    ),
                )


                assert (
                    cursor.fetchone()[
                        0
                    ]
                    == 0
                )


                cursor.execute(
                    """
                    select
                        status,
                        intent

                    from public.tickets

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                assert cursor.fetchone() == (
                    "WAITING_CUSTOMER",
                    "order_status",
                )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )


def test_verified_order_status_creates_safe_commerce_draft(
    monkeypatch,
):

    install_dependencies(
        monkeypatch
    )


    ticket_id = None


    try:

        ticket_id, message_id = (
            create_ticket(
                body=
                    (
                        "Where is order "
                        "#NS10041?"
                    ),

                customer_hint=
                    "amina.demo@example.com",
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


        assert (
            verification.status_code
            == 200
        )

        assert (
            verification.json()[
                "verified"
            ]
            is True
        )


        response = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/messages/"
                + message_id
                + "/ai-draft"
            )
        )


        assert response.status_code == 200


        result = response.json()


        assert (
            result[
                "decision"
            ]
            == "AUTO_RESPOND"
        )

        assert (
            "AUTO_RESPONSE_ELIGIBLE"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "AUTO_RESPONSE:VERIFIED_ORDER_STATUS"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            result[
                "safe_draft_ready"
            ]
            is True
        )

        assert (
            result[
                "confidence_band"
            ]
            == "HIGH"
        )

        assert (
            result[
                "generation_attempted"
            ]
            is False
        )


        order = result[
            "commerce_order"
        ]


        assert order is not None

        assert (
            order[
                "order_number"
            ]
            == "#NS10041"
        )

        assert (
            order[
                "status"
            ]
            == "IN_TRANSIT"
        )

        assert (
            order[
                "tracking_number"
            ]
            == "TRK-DEMO-10041"
        )


        answer = result[
            "answer"
        ][
            "answer"
        ]


        assert (
            "in transit"
            in answer.lower()
        )

        assert (
            "TRK-DEMO-10041"
            in answer
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        status,
                        intent,
                        confidence_band

                    from public.tickets

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                assert cursor.fetchone() == (
                    "DRAFTED",
                    "order_status",
                    "HIGH",
                )


                cursor.execute(
                    """
                    select
                        status,
                        tool_name

                    from public.tool_calls

                    where ai_run_id = %s;
                    """,
                    (
                        result[
                            "ai_run_id"
                        ],
                    ),
                )


                assert cursor.fetchone() == (
                    "SUCCEEDED",
                    "commerce.lookup_order",
                )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )


def test_failed_identity_never_exposes_order_facts(
    monkeypatch,
):

    install_dependencies(
        monkeypatch
    )


    ticket_id = None


    try:

        ticket_id, message_id = (
            create_ticket(
                body=
                    (
                        "Where is order "
                        "#NS10043?"
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


        assert (
            verification.status_code
            == 200
        )

        assert (
            verification.json()[
                "verified"
            ]
            is False
        )


        response = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/messages/"
                + message_id
                + "/ai-draft"
            )
        )


        assert response.status_code == 200


        result = response.json()


        assert (
            result[
                "decision"
            ]
            == "REQUEST_CLARIFICATION"
        )

        assert (
            result[
                "commerce_order"
            ]
            is None
        )


        body = str(
            result
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
            "101.0"
            not in body
        )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )