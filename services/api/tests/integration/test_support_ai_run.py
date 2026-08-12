from dataclasses import dataclass
from datetime import (
    datetime,
    timezone,
)
from uuid import (
    UUID,
    uuid4,
)

import psycopg

from fastapi.testclient import TestClient

from app.core.auth import (
    get_current_internal_user,
)

from app.core.config import settings

from app.main import app

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.grounded_generation import (
    GroundedModelOutput,
)

from app.services.embeddings import (
    EmbeddingBatch,
)

from app.services.generation import (
    GenerationResult,
)


client = TestClient(app)


MANAGER_ID = UUID(
    "66666666-6666-4666-8666-666666666666"
)


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m3e-manager@test.local",

        name=
            "M3E Test Manager",

        role=
            "SUPPORT_MANAGER",
    )


def basis_vector(
    index: int,
) -> list[float]:

    vector = [
        0.0
        for _ in range(
            1536
        )
    ]


    vector[
        index
    ] = 1.0


    return vector


def vector_literal(
    vector: list[float],
) -> str:

    return (
        "["
        + ",".join(
            str(
                value
            )
            for value
            in vector
        )
        + "]"
    )


@dataclass
class FakeEmbeddingProvider:

    provider_name: str = (
        "decision-test"
    )

    model: str = (
        "decision-test-v1"
    )

    dimensions: int = 1536


    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        return basis_vector(
            0
        )


    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:

        return EmbeddingBatch(
            vectors=[
                basis_vector(
                    0
                )
                for _ in texts
            ],

            prompt_tokens=
                0,
        )


@dataclass
class FakeGenerationProvider:

    provider_name: str = (
        "generation-test"
    )

    model: str = (
        "generation-test-v1"
    )


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ) -> GenerationResult:

        return GenerationResult(
            output=
                GroundedModelOutput(
                    status=
                        "ANSWERED",

                    answer=(
                        "Yes. Unused items "
                        "may be returned "
                        "within 30 days."
                    ),

                    citation_refs=[
                        "K1",
                    ],
                ),

            input_tokens=
                100,

            output_tokens=
                20,

            generation_ms=
                10.0,
        )


def cleanup(
    *,
    ticket_id: str | None,
    source_id: str | None,
) -> None:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            if ticket_id:

                cursor.execute(
                    """
                    delete
                    from public.audit_events

                    where
                        metadata ->> 'ticket_id'
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


            if source_id:

                cursor.execute(
                    """
                    delete
                    from public.audit_events

                    where entity_type =
                        'knowledge_source'

                      and entity_id = %s;
                    """,
                    (
                        source_id,
                    ),
                )


                cursor.execute(
                    """
                    delete
                    from public.knowledge_sources

                    where id = %s;
                    """,
                    (
                        source_id,
                    ),
                )


def test_ai_run_persists_grounding_and_evidence(
    monkeypatch,
):

    embedding_provider = (
        FakeEmbeddingProvider()
    )


    generation_provider = (
        FakeGenerationProvider()
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


    source_id = None
    ticket_id = None


    try:

        # --------------------------------------------------
        # Create one deterministic published policy source.
        # --------------------------------------------------

        source_response = client.post(
            "/api/v1/agent/knowledge/sources",

            json={
                "title":
                    (
                        "M3E Persistence Test "
                        + str(
                            uuid4()
                        )
                    ),

                "type":
                    "POLICY",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Eligibility",

                        "content":
                            (
                                "Unused items may "
                                "be returned within "
                                "30 days."
                            ),

                        "metadata": {
                            "claim_key":
                                "return_window_days",

                            "claim_value":
                                30,
                        },
                    }
                ],
            },
        )


        assert (
            source_response.status_code
            == 201
        )


        source_id = (
            source_response
            .json()[
                "id"
            ]
        )


        # --------------------------------------------------
        # Publish the source so retrieval is allowed to use
        # it.
        # --------------------------------------------------

        publish_response = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/publish"
            )
        )


        assert (
            publish_response.status_code
            == 200
        )


        # --------------------------------------------------
        # Install a deterministic embedding directly.
        #
        # The fake embedding provider also returns basis
        # vector 0, so this source should rank with HIGH
        # similarity.
        # --------------------------------------------------

        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    update public.knowledge_chunks

                    set
                        embedding =
                            %s::extensions.vector,

                        content_checksum =
                            repeat('a', 64),

                        index_fingerprint =
                            repeat('b', 64),

                        embedding_provider =
                            'decision-test',

                        embedding_model =
                            'decision-test-v1',

                        embedding_dimensions =
                            1536,

                        embedded_at =
                            now()

                    where source_id = %s;
                    """,
                    (
                        vector_literal(
                            basis_vector(
                                0
                            )
                        ),

                        source_id,
                    ),
                )


        # --------------------------------------------------
        # Create an inbound return-policy question.
        #
        # M4D should classify this as:
        #
        # intent = return
        # commerce_required = false
        #
        # Therefore it should use the normal RAG path.
        # --------------------------------------------------

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
                    "m3e-test@example.com",

                "subject":
                    None,

                "body":
                    (
                        "Can I return an "
                        "unused item after "
                        "18 days?"
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


        # --------------------------------------------------
        # Run unified support AI decisioning.
        # --------------------------------------------------

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


        result = (
            response.json()
        )


        # ==================================================
        # Grounding / evidence assertions.
        # ==================================================

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
            is True
        )


        assert (
            result[
                "answer"
            ][
                "status"
            ]
            == "ANSWERED"
        )


        assert (
            result[
                "evidence_count"
            ]
            >= 1
        )


        # ==================================================
        # M4D classification assertions.
        # ==================================================

        assert (
            result[
                "intent"
            ]
            == "return"
        )


        assert (
            result[
                "commerce_required"
            ]
            is False
        )


        # ==================================================
        # M4D unified decision assertions.
        #
        # This is a safe grounded draft, but M4E has not yet
        # authorized automatic sending.
        # ==================================================
        assert (
            result[
                "decision"
            ]
            == "AUTO_RESPOND"
        )

        assert (
            result[
                "safe_draft_ready"
            ]
            is True
        )


        assert (
            "EVIDENCE_HIGH"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "SAFE_KNOWLEDGE_DRAFT"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "AUTO_RESPONSE_ELIGIBLE"
            in result[
                "decision_reasons"
            ]
        )


        assert (
            "AUTO_RESPONSE:KNOWLEDGE_RETURN"
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

                # ==========================================
                # AI run persistence.
                # ==========================================

                cursor.execute(
                    """
                    select
                        confidence_band,
                        decision,
                        provider,
                        model,
                        intent

                    from public.ai_runs

                    where id = %s;
                    """,
                    (
                        ai_run_id,
                    ),
                )


                row = (
                    cursor.fetchone()
                )


                assert row == (
                    "HIGH",
                    "AUTO_RESPOND",
                    "generation-test",
                    "generation-test-v1",
                    "return",
                )


                # ==========================================
                # Retrieval evidence persistence.
                # ==========================================

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


                evidence_count = (
                    cursor.fetchone()[
                        0
                    ]
                )


                assert (
                    evidence_count
                    >= 1
                )


                # ==========================================
                # M4D decision audit persistence.
                #
                # M3E previously used:
                # AI_DRAFT_EVALUATED
                #
                # M4D now uses:
                # SUPPORT_DECISION_EVALUATED
                # ==========================================

                cursor.execute(
                    """
                    select count(*)::int

                    from public.audit_events

                    where entity_type =
                        'ai_run'

                      and entity_id = %s

                      and event_type =
                        'SUPPORT_DECISION_EVALUATED';
                    """,
                    (
                        ai_run_id,
                    ),
                )


                assert (
                    cursor.fetchone()[
                        0
                    ]
                    == 1
                )


                # ==========================================
                # Ticket operational state must also reflect
                # the unified decision.
                # ==========================================

                cursor.execute(
                    """
                    select
                        status,
                        intent,
                        confidence_band,
                        restricted_action

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
                    "DRAFTED",
                    "return",
                    "HIGH",
                    False,
                )


    finally:

        app.dependency_overrides.clear()


        cleanup(
            ticket_id=
                ticket_id,

            source_id=
                source_id,
        )