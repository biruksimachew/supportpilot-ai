from uuid import UUID, uuid4

import psycopg
from fastapi.testclient import TestClient

from app.core.auth import (
    get_current_internal_user,
)
from app.core.config import settings
from app.main import app
from app.schemas.auth import InternalUser
from app.schemas.intake import (
    InboundMessageRequest,
)
from app.services.intake import (
    ingest_inbound_message,
)


client = TestClient(app)


TEST_AGENT_ID = UUID(
    "11111111-1111-4111-8111-111111111111"
)


def fake_internal_user() -> InternalUser:
    return InternalUser(
        id=TEST_AGENT_ID,
        email="agent@test.local",
        name="Queue Test Agent",
        role="SUPPORT_AGENT",
    )


def cleanup_threads(
    thread_ids: list[str],
) -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.audit_events
                where metadata ->> 'external_thread_id'
                    = any(%s);
                """,
                (thread_ids,),
            )

            cursor.execute(
                """
                delete from public.tickets
                where external_thread_id
                    = any(%s);
                """,
                (thread_ids,),
            )


def test_agent_endpoints_require_authentication() -> None:
    response = client.get(
        "/api/v1/agent/tickets"
    )

    assert response.status_code == 401


def test_agent_queue_and_ticket_detail() -> None:
    thread_p2 = (
        f"agent-queue-p2-{uuid4()}"
    )

    thread_p4 = (
        f"agent-queue-p4-{uuid4()}"
    )

    thread_ids = [
        thread_p2,
        thread_p4,
    ]

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_internal_user

    try:
        p2 = ingest_inbound_message(
            InboundMessageRequest(
                channel="chat",
                external_message_id=(
                    f"message-{uuid4()}"
                ),
                external_thread_id=
                    thread_p2,
                customer_hint=(
                    "amina.demo@example.com"
                ),
                body=(
                    "My item arrived damaged."
                ),
                received_at=(
                    "2026-08-10T08:00:00Z"
                ),
                attachments=[],
                metadata={
                    "test": True,
                },
            )
        )

        p4 = ingest_inbound_message(
            InboundMessageRequest(
                channel="chat",
                external_message_id=(
                    f"message-{uuid4()}"
                ),
                external_thread_id=
                    thread_p4,
                customer_hint=(
                    "daniel.demo@example.com"
                ),
                body=(
                    "What is your shipping policy?"
                ),
                received_at=(
                    "2026-08-10T08:01:00Z"
                ),
                attachments=[],
                metadata={
                    "test": True,
                },
            )
        )

        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    update public.tickets
                    set
                        priority = 'P2',
                        status = 'REVIEW_REQUIRED',
                        intent = 'damaged_item'
                    where id = %s;
                    """,
                    (p2.ticket_id,),
                )

        queue = client.get(
            "/api/v1/agent/tickets"
        )

        assert queue.status_code == 200

        queue_result = queue.json()

        test_items = [
            item
            for item
            in queue_result["items"]
            if item["id"]
            in {
                str(p2.ticket_id),
                str(p4.ticket_id),
            }
        ]

        assert len(
            test_items
        ) == 2

        assert (
            test_items[0]["id"]
            == str(p2.ticket_id)
        )

        assert (
            test_items[0]["priority"]
            == "P2"
        )

        detail = client.get(
            (
                "/api/v1/agent/tickets/"
                f"{p2.ticket_id}"
            )
        )

        assert detail.status_code == 200

        detail_result = detail.json()

        assert (
            detail_result["id"]
            == str(p2.ticket_id)
        )

        assert (
            detail_result["status"]
            == "REVIEW_REQUIRED"
        )

        assert len(
            detail_result["messages"]
        ) == 1

        assert (
            detail_result["messages"][0]["body"]
            == "My item arrived damaged."
        )

    finally:
        app.dependency_overrides.clear()

        cleanup_threads(
            thread_ids
        )