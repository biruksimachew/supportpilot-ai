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
            "delivery-agent@test.local",

        name=
            "Delivery Test Agent",

        role=
            "SUPPORT_AGENT",
    )


def test_chat_delivery_is_idempotent() -> None:

    thread_id = (
        str(
            uuid4()
        )
    )

    external_message_id = (
        "delivery-test:"
        + str(
            uuid4()
        )
    )


    result = ingest_inbound_message(
        InboundMessageRequest(
            channel=
                "chat",

            external_message_id=
                external_message_id,

            external_thread_id=
                thread_id,

            customer_hint=
                "amina.demo@example.com",

            body=
                "Can you help me?",

            received_at=
                "2026-08-13T09:00:00Z",

            attachments=[],

            metadata={
                "test":
                    True,
            },
        )
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
                        "Thanks for contacting "
                        "Northstar support."
                    ),
            },
        )


        assert (
            response.status_code
            == 200
        )


        first = (
            response.json()
        )


        assert (
            first["status"]
            == "DELIVERED"
        )


        assert (
            first[
                "ticket_status"
            ]
            == "WAITING_CUSTOMER"
        )


        assert (
            first[
                "idempotent_replay"
            ]
            is False
        )


        replay = client.post(
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
                        "Thanks for contacting "
                        "Northstar support."
                    ),
            },
        )


        assert (
            replay.status_code
            == 200
        )


        second = (
            replay.json()
        )


        assert (
            second[
                "delivery_id"
            ]
            == first[
                "delivery_id"
            ]
        )


        assert (
            second[
                "message_id"
            ]
            == first[
                "message_id"
            ]
        )


        assert (
            second[
                "idempotent_replay"
            ]
            is True
        )


        conflict = client.post(
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
                    "Different reply.",
            },
        )


        assert (
            conflict.status_code
            == 409
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

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


                cursor.execute(
                    """
                    select count(*)

                    from public.outbound_deliveries

                    where ticket_id = %s

                      and status =
                          'DELIVERED';
                    """,
                    (
                        result.ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[0]
                    == 1
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
                    == "WAITING_CUSTOMER"
                )


    finally:

        app.dependency_overrides.clear()


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
                            result.ticket_id
                        ),
                    ),
                )


                cursor.execute(
                    """
                    delete from public.tickets

                    where id = %s;
                    """,
                    (
                        result.ticket_id,
                    ),
                )