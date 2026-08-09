import uuid

import psycopg
from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app


client = TestClient(app)


def cleanup_chat_session(
    session_id: str,
) -> None:
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
                (session_id,),
            )

            cursor.execute(
                """
                delete from public.tickets
                where channel = 'chat'
                  and external_thread_id = %s;
                """,
                (session_id,),
            )


def create_session() -> dict:
    response = client.post(
        "/api/v1/chat/sessions"
    )

    assert response.status_code == 201

    return response.json()


def test_chat_session_message_retry_and_history() -> None:
    session = create_session()

    session_id = session["session_id"]
    token = session["session_token"]

    headers = {
        "X-Chat-Session-Token": token,
    }

    client_message_id = str(
        uuid.uuid4()
    )

    payload = {
        "client_message_id":
            client_message_id,
        "body":
            "Where is my order #NS10041?",
        "customer_hint":
            "amina.demo@example.com",
    }

    try:
        first = client.post(
            (
                f"/api/v1/chat/sessions/"
                f"{session_id}/messages"
            ),
            headers=headers,
            json=payload,
        )

        assert first.status_code == 201

        first_result = first.json()

        assert first_result[
            "duplicate"
        ] is False

        assert first_result[
            "created_ticket"
        ] is True

        retry = client.post(
            (
                f"/api/v1/chat/sessions/"
                f"{session_id}/messages"
            ),
            headers=headers,
            json=payload,
        )

        assert retry.status_code == 200

        retry_result = retry.json()

        assert retry_result[
            "duplicate"
        ] is True

        assert (
            retry_result["message_id"]
            == first_result["message_id"]
        )

        assert (
            retry_result["ticket_id"]
            == first_result["ticket_id"]
        )

        history = client.get(
            (
                f"/api/v1/chat/sessions/"
                f"{session_id}/messages"
            ),
            headers=headers,
        )

        assert history.status_code == 200

        history_result = history.json()

        assert len(
            history_result["messages"]
        ) == 1

        assert (
            history_result["messages"][0]["body"]
            == "Where is my order #NS10041?"
        )

        # Internal agent notes must never appear publicly.
        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    insert into public.messages (
                        ticket_id,
                        direction,
                        sender_type,
                        body,
                        is_internal,
                        received_at
                    )
                    values (
                        %s,
                        'outbound',
                        'agent',
                        'INTERNAL TEST NOTE',
                        true,
                        timezone('utc', now())
                    );
                    """,
                    (
                        first_result[
                            "ticket_id"
                        ],
                    ),
                )

        history_after_note = client.get(
            (
                f"/api/v1/chat/sessions/"
                f"{session_id}/messages"
            ),
            headers=headers,
        )

        assert (
            history_after_note.status_code
            == 200
        )

        visible_messages = (
            history_after_note
            .json()["messages"]
        )

        assert len(
            visible_messages
        ) == 1

        assert all(
            item["body"]
            != "INTERNAL TEST NOTE"
            for item in visible_messages
        )

    finally:
        cleanup_chat_session(
            session_id
        )


def test_chat_session_token_cannot_access_another_session() -> None:
    first_session = create_session()
    second_session = create_session()

    response = client.get(
        (
            f"/api/v1/chat/sessions/"
            f"{first_session['session_id']}"
            f"/messages"
        ),
        headers={
            "X-Chat-Session-Token":
                second_session["session_token"]
        },
    )

    assert response.status_code == 403