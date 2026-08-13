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

from app.schemas.intake import (
    InboundMessageRequest,
)

from app.services.email_outbound import (
    EmailOutboundResult,
    EmailOutboundUncertainError,
)

from app.services.intake import (
    ingest_inbound_message,
)


client = TestClient(
    app
)


TEST_AGENT_ID = UUID(
    "77777777-7777-4777-8777-777777777777"
)


def fake_agent() -> InternalUser:

    return InternalUser(
        id=
            TEST_AGENT_ID,

        email=
            "email-delivery-agent@test.local",

        name=
            "Email Delivery Test Agent",

        role=
            "SUPPORT_AGENT",
    )


def _create_email_ticket():

    return ingest_inbound_message(
        InboundMessageRequest(
            channel=
                "email",

            external_message_id=
                (
                    "gmail:"
                    + uuid4().hex
                ),

            external_thread_id=
                (
                    "gmail:"
                    + uuid4().hex
                ),

            customer_hint=
                "amina.demo@example.com",

            subject=
                "TrailPack question",

            body=
                "Is the TrailPack waterproof?",

            received_at=
                "2026-08-13T10:00:00Z",

            attachments=[],

            metadata={
                "provider":
                    "gmail",

                "test":
                    True,
            },
        )
    )


def _cleanup(
    ticket_id: UUID,
) -> None:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                delete from public.audit_events

                where metadata
                    ->> 'ticket_id'
                    = %s;
                """,
                (
                    str(
                        ticket_id
                    ),
                ),
            )


            cursor.execute(
                """
                delete from public.tickets

                where id = %s;
                """,
                (
                    ticket_id,
                ),
            )


def test_email_delivery_success(
    monkeypatch,
) -> None:

    result = (
        _create_email_ticket()
    )


    def fake_delivery(
        **kwargs,
    ) -> EmailOutboundResult:

        assert (
            kwargs[
                "thread_id"
            ]
        )

        assert (
            kwargs[
                "message_id"
            ]
        )

        assert (
            kwargs[
                "destination"
            ]
            == "amina.demo@example.com"
        )
        assert not (
            kwargs[
                "message_id"
            ].startswith(
                "gmail:"
            )
        )


        assert not (
            kwargs[
                "thread_id"
            ].startswith(
                "gmail:"
            )
        )



        return EmailOutboundResult(
            provider_message_id=
                (
                    "gmail-provider-"
                    + str(
                        uuid4()
                    )
                ),

            provider_thread_id=
                kwargs[
                    "thread_id"
                ],
        )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "validate_email_outbound_configuration"
        ),
        lambda: None,
    )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "deliver_email_via_n8n"
        ),
        fake_delivery,
    )


    app.dependency_overrides[
        get_current_internal_user
    ] = fake_agent


    request_key = (
        uuid4()
    )


    try:

        response = client.post(
            (
                "/api/v1/agent/tickets/"
                f"{result.ticket_id}"
                "/send"
            ),

            json={
                "idempotency_key":
                    str(
                        request_key
                    ),

                "body":
                    (
                        "The TrailPack is "
                        "water-resistant, "
                        "not waterproof."
                    ),
            },
        )


        assert (
            response.status_code
            == 200
        )


        payload = response.json()


        assert (
            payload["status"]
            == "DELIVERED"
        )


        assert (
            payload["channel"]
            == "email"
        )


        assert (
            payload[
                "ticket_status"
            ]
            == "WAITING_CUSTOMER"
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        status,
                        attempt_count,
                        provider_message_id

                    from public.outbound_deliveries

                    where ticket_id = %s;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                delivery = (
                    cursor.fetchone()
                )


                assert (
                    delivery[0]
                    == "DELIVERED"
                )


                assert (
                    delivery[1]
                    == 1
                )


                assert (
                    delivery[2]
                )


                cursor.execute(
                    """
                    select count(*)

                    from public.messages

                    where ticket_id = %s

                      and direction =
                          'outbound'

                      and is_internal =
                          false;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[0]
                    == 1
                )


    finally:

        app.dependency_overrides.clear()

        _cleanup(
            result.ticket_id
        )


def test_uncertain_email_is_not_persisted_as_sent(
    monkeypatch,
) -> None:

    result = (
        _create_email_ticket()
    )


    def uncertain_delivery(
        **_kwargs,
    ):

        raise EmailOutboundUncertainError(
            "synthetic timeout"
        )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "validate_email_outbound_configuration"
        ),
        lambda: None,
    )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "deliver_email_via_n8n"
        ),
        uncertain_delivery,
    )


    app.dependency_overrides[
        get_current_internal_user
    ] = fake_agent


    request_key = (
        uuid4()
    )


    try:

        response = client.post(
            (
                "/api/v1/agent/tickets/"
                f"{result.ticket_id}"
                "/send"
            ),

            json={
                "idempotency_key":
                    str(
                        request_key
                    ),

                "body":
                    "Synthetic reply.",
            },
        )


        assert (
            response.status_code
            == 503
        )


        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            == "DELIVERY_UNCERTAIN"
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select status

                    from public.outbound_deliveries

                    where ticket_id = %s;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[0]
                    == "UNCERTAIN"
                )


                cursor.execute(
                    """
                    select count(*)

                    from public.messages

                    where ticket_id = %s

                      and direction =
                          'outbound'

                      and is_internal =
                          false;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[0]
                    == 0
                )


                cursor.execute(
                    """
                    select status

                    from public.tickets

                    where id = %s;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[0]
                    != "WAITING_CUSTOMER"
                )


        retry = client.post(
            (
                "/api/v1/agent/tickets/"
                f"{result.ticket_id}"
                "/send"
            ),

            json={
                "idempotency_key":
                    str(
                        request_key
                    ),

                "body":
                    "Synthetic reply.",
            },
        )


        assert (
            retry.status_code
            == 409
        )


    finally:

        app.dependency_overrides.clear()

        _cleanup(
            result.ticket_id
        )

def test_confirmed_email_failure_can_retry_same_delivery(
    monkeypatch,
) -> None:

    result = (
        _create_email_ticket()
    )

    attempts = {
        "count": 0,
    }


    def controlled_delivery(
        **kwargs,
    ) -> EmailOutboundResult:

        attempts["count"] += 1

        if attempts["count"] == 1:
            from app.services.email_outbound import (
                EmailOutboundConfirmedFailure,
            )

            raise EmailOutboundConfirmedFailure(
                "synthetic confirmed rejection"
            )

        return EmailOutboundResult(
            provider_message_id=
                (
                    "gmail-provider-"
                    + str(
                        uuid4()
                    )
                ),

            provider_thread_id=
                kwargs[
                    "thread_id"
                ],
        )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "validate_email_outbound_configuration"
        ),
        lambda: None,
    )


    monkeypatch.setattr(
        (
            "app.services."
            "outbound_delivery."
            "deliver_email_via_n8n"
        ),
        controlled_delivery,
    )


    app.dependency_overrides[
        get_current_internal_user
    ] = fake_agent


    request_key = (
        uuid4()
    )


    try:

        first = client.post(
            (
                "/api/v1/agent/tickets/"
                f"{result.ticket_id}"
                "/send"
            ),

            json={
                "idempotency_key":
                    str(
                        request_key
                    ),

                "body":
                    "Synthetic retry reply.",
            },
        )


        assert (
            first.status_code
            == 502
        )


        assert (
            first.json()[
                "detail"
            ][
                "code"
            ]
            == "DELIVERY_CONFIRMED_FAILED"
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        id,
                        status,
                        attempt_count

                    from public.outbound_deliveries

                    where ticket_id = %s;
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                failed = (
                    cursor.fetchone()
                )


                first_delivery_id = (
                    failed[0]
                )


                assert (
                    failed[1]
                    == "FAILED"
                )

                assert (
                    failed[2]
                    == 1
                )


        retry = client.post(
            (
                "/api/v1/agent/tickets/"
                f"{result.ticket_id}"
                "/send"
            ),

            json={
                "idempotency_key":
                    str(
                        request_key
                    ),

                "body":
                    "Synthetic retry reply.",
            },
        )


        assert (
            retry.status_code
            == 200
        )


        retry_payload = (
            retry.json()
        )


        assert (
            retry_payload[
                "status"
            ]
            == "DELIVERED"
        )


        assert (
            retry_payload[
                "delivery_id"
            ]
            == str(
                first_delivery_id
            )
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select
                        status,
                        attempt_count

                    from public.outbound_deliveries

                    where id = %s;
                    """,
                    (
                        first_delivery_id,
                    ),
                )


                final = (
                    cursor.fetchone()
                )


                assert (
                    final[0]
                    == "DELIVERED"
                )

                assert (
                    final[1]
                    == 2
                )


    finally:

        app.dependency_overrides.clear()

        _cleanup(
            result.ticket_id
        )