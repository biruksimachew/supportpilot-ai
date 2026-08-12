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
    "99999999-9999-4999-8999-999999999999"
)


class NeverCalledEmbeddingProvider:

    provider_name = (
        "must-not-run"
    )

    model = (
        "must-not-run"
    )

    dimensions = 1536


    def embed_query(
        self,
        text: str,
    ):
        raise AssertionError(
            (
                "Embedding provider was called "
                "for a restricted action."
            )
        )


    def embed(
        self,
        texts,
    ):
        raise AssertionError(
            (
                "Embedding provider was called "
                "for a restricted action."
            )
        )


class NeverCalledGenerationProvider:

    provider_name = (
        "must-not-run"
    )

    model = (
        "must-not-run"
    )


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):
        raise AssertionError(
            (
                "Generation provider was called "
                "for a restricted action."
            )
        )


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m4c-manager@test.local",

        name=
            "M4C Test Manager",

        role=
            "SUPPORT_MANAGER",
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

                where metadata ->> 'ticket_id'
                    = %s

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


def test_refund_request_is_blocked_before_rag_and_generation(
    monkeypatch,
):

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


    ticket_id = None


    try:

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
                    "daniel.demo@example.com",

                "subject":
                    None,

                "body":
                    "Refund #NS10042 now.",

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


        response = client.post(
            (
                "/api/v1/agent/tickets/"
                + ticket_id
                + "/messages/"
                + message_id
                + "/ai-draft"
            )
        )


        assert (
            response.status_code
            == 200
        )


        result = response.json()


        assert (
            result[
                "decision"
            ]
            == "REVIEW_REQUIRED"
        )


        assert (
            result[
                "generation_attempted"
            ]
            is False
        )


        assert (
            result[
                "evidence_count"
            ]
            == 0
        )


        assert (
            "RESTRICTED_ACTION_DETECTED"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "RESTRICTED_ACTION:REFUND"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "HUMAN_ACTION_REQUIRED"
            in result[
                "decision_reasons"
            ]
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

                # ------------------------------------------
                # Ticket must be escalated.
                # ------------------------------------------

                cursor.execute(
                    """
                    select
                        restricted_action,
                        status,
                        escalation_reason

                    from public.tickets

                    where id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                ticket = (
                    cursor.fetchone()
                )


                assert ticket == (
                    True,
                    "REVIEW_REQUIRED",
                    "RESTRICTED_ACTION:REFUND",
                )


                # ------------------------------------------
                # AI run must identify itself as a
                # deterministic policy decision—not Ollama.
                # ------------------------------------------

                cursor.execute(
                    """
                    select
                        provider,
                        model,
                        decision,
                        confidence_band

                    from public.ai_runs

                    where id = %s;
                    """,
                    (
                        ai_run_id,
                    ),
                )


                ai_run = (
                    cursor.fetchone()
                )


                assert ai_run == (
                    "deterministic-policy",
                    "restricted-action-v1",
                    "REVIEW_REQUIRED",
                    "LOW",
                )


                # ------------------------------------------
                # Restricted action should have performed
                # no knowledge retrieval.
                # ------------------------------------------

                cursor.execute(
                    """
                    select count(*)::int

                    from public.retrieval_evidence

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


                # ------------------------------------------
                # No commerce tool call should exist.
                # ------------------------------------------

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


                # ------------------------------------------
                # Restricted-action audit must exist.
                # ------------------------------------------

                cursor.execute(
                    """
                    select count(*)::int

                    from public.audit_events

                    where event_type =
                        'RESTRICTED_ACTION_DETECTED'

                      and entity_type =
                        'ticket'

                      and entity_id = %s;
                    """,
                    (
                        ticket_id,
                    ),
                )


                assert (
                    cursor.fetchone()[
                        0
                    ]
                    == 1
                )


    finally:

        app.dependency_overrides.clear()


        if ticket_id:

            cleanup_ticket(
                ticket_id
            )