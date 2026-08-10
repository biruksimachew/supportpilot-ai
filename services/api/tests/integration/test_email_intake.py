from uuid import uuid4

import psycopg
from fastapi.testclient import (
    TestClient,
)

from app.core.config import settings
from app.main import app


client = TestClient(app)


def cleanup_thread(
    external_thread_id: str,
) -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete
                from public.audit_events
                where metadata ->> 'external_thread_id'
                    = %s;
                """,
                (external_thread_id,),
            )

            cursor.execute(
                """
                delete
                from public.tickets
                where external_thread_id
                    = %s;
                """,
                (external_thread_id,),
            )


def test_email_ingest_requires_secret() -> None:
    response = client.post(
        "/api/v1/integrations/email/messages",
        json={
            "provider": "gmail",
            "external_message_id":
                f"message-{uuid4()}",
            "external_thread_id":
                f"thread-{uuid4()}",
            "from_email":
                "customer@example.com",
            "subject":
                "Order question",
            "body":
                "Where is my order?",
            "received_at":
                "2026-08-10T10:00:00Z",
        },
    )

    assert response.status_code == 401


def test_email_ingest_is_idempotent_and_reuses_thread() -> None:
    provider_thread_id = f"thread-{uuid4()}"

    normalized_thread_id = f"gmail:{provider_thread_id}"

    first_message_id = f"message-{uuid4()}"

    second_message_id = f"message-{uuid4()}"

    headers = {
        "X-SupportPilot-Ingest-Secret":
            settings.email_ingest_secret,
    }

    try:
        first_payload = {
            "provider": "gmail",
            "external_message_id":
                first_message_id,
            "external_thread_id":
                provider_thread_id,
            "from_email":
                "amina.demo@example.com",
            "from_name":
                "Amina Tesfaye",
            "subject":
                "Order #NS10041",
            "body":
                "Where is my order #NS10041?",
            "received_at":
                "2026-08-10T10:00:00Z",
            "attachments": [],
            "metadata": {
                "test": True,
            },
        }

        first = client.post(
            "/api/v1/integrations/email/messages",
            headers=headers,
            json=first_payload,
        )

        assert first.status_code == 201

        first_result = first.json()


        assert (
            first_result["duplicate"]
            is False
        )

        assert (
            first_result["created_ticket"]
            is True
        )

        duplicate = client.post(
            "/api/v1/integrations/email/messages",
            headers=headers,
            json=first_payload,
        )

        assert duplicate.status_code == 200

        duplicate_result = duplicate.json()

        assert (
            duplicate_result["duplicate"]
            is True
        )

        assert (
            duplicate_result["ticket_id"]
            ==
            first_result["ticket_id"]
        )

        assert (
            duplicate_result["message_id"]
            ==
            first_result["message_id"]
        )

        second = client.post(
            "/api/v1/integrations/email/messages",
            headers=headers,
            json={
                "provider":
                    "gmail",
                "external_message_id":
                    second_message_id,
                "external_thread_id":
                    provider_thread_id,
                "from_email":
                    "amina.demo@example.com",
                "subject":
                    "Re: Order #NS10041",
                "body":
                    "Can you send the tracking number?",
                "received_at":
                    "2026-08-10T10:05:00Z",
                "attachments": [],
                "metadata": {
                    "test": True,
                },
            },
        )

        assert second.status_code == 201

        second_result = second.json()

        assert (
            second_result["ticket_id"]
            ==
            first_result["ticket_id"]
        )

        assert (
            second_result["message_id"]
            !=
            first_result["message_id"]
        )

        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select count(*)
                    from public.tickets
                    where channel = 'email'
                      and external_thread_id = %s;
                    """,
                    (
                        normalized_thread_id,
                    ),
                )

                assert (
                    cursor.fetchone()[0]
                    == 1
                )

                cursor.execute(
                    """
                    select count(*)
                    from public.messages as m
                    join public.tickets as t
                      on t.id = m.ticket_id
                    where t.channel = 'email'
                      and t.external_thread_id = %s;
                    """,
                    (
                        normalized_thread_id,
                    ),
                )

                assert (
                    cursor.fetchone()[0]
                    == 2
                )

    finally:
        cleanup_thread(
            normalized_thread_id
        )