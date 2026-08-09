import psycopg
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


client = TestClient(app)


TEST_THREAD_ID = "m2a-chat-session-001"
TEST_MESSAGE_1 = "m2a-chat-message-001"
TEST_MESSAGE_2 = "m2a-chat-message-002"


def cleanup_test_data() -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                delete from public.audit_events
                where metadata ->> 'external_thread_id'
                    = %s;
                """,
                (TEST_THREAD_ID,),
            )

            cursor.execute(
                """
                delete from public.tickets
                where channel = 'chat'
                  and external_thread_id = %s;
                """,
                (TEST_THREAD_ID,),
            )


def test_chat_intake_is_idempotent_and_reuses_ticket() -> None:
    cleanup_test_data()

    try:
        first_payload = {
            "channel": "chat",
            "external_message_id": TEST_MESSAGE_1,
            "external_thread_id": TEST_THREAD_ID,
            "customer_hint": "amina.demo@example.com",
            "body": "Where is my order #NS10041?",
            "received_at": "2026-08-09T16:00:00Z",
            "attachments": [],
            "metadata": {
                "test": True
            },
        }

        first = client.post(
            "/api/v1/intake/messages",
            json=first_payload,
        )

        assert first.status_code == 201

        first_result = first.json()

        assert first_result["duplicate"] is False
        assert first_result["created_ticket"] is True
        assert first_result["ticket_status"] == "NEW"

        duplicate = client.post(
            "/api/v1/intake/messages",
            json=first_payload,
        )

        assert duplicate.status_code == 200

        duplicate_result = duplicate.json()

        assert duplicate_result["duplicate"] is True
        assert (
            duplicate_result["ticket_id"]
            == first_result["ticket_id"]
        )
        assert (
            duplicate_result["message_id"]
            == first_result["message_id"]
        )

        second_payload = {
            "channel": "chat",
            "external_message_id": TEST_MESSAGE_2,
            "external_thread_id": TEST_THREAD_ID,
            "customer_hint": "amina.demo@example.com",
            "body": "Do you have the tracking number?",
            "received_at": "2026-08-09T16:01:00Z",
            "attachments": [],
            "metadata": {
                "test": True
            },
        }

        second = client.post(
            "/api/v1/intake/messages",
            json=second_payload,
        )

        assert second.status_code == 201

        second_result = second.json()

        assert second_result["duplicate"] is False
        assert second_result["created_ticket"] is False

        assert (
            second_result["ticket_id"]
            == first_result["ticket_id"]
        )

        assert (
            second_result["message_id"]
            != first_result["message_id"]
        )

        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select count(*)
                    from public.tickets
                    where channel = 'chat'
                      and external_thread_id = %s;
                    """,
                    (TEST_THREAD_ID,),
                )

                assert cursor.fetchone()[0] == 1

                cursor.execute(
                    """
                    select count(*)
                    from public.messages
                    where ticket_id = %s;
                    """,
                    (first_result["ticket_id"],),
                )

                assert cursor.fetchone()[0] == 2

    finally:
        cleanup_test_data()