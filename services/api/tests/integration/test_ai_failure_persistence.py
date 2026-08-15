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

from app.schemas.grounded_generation import (
    GroundedModelOutput,
)

from app.services.embeddings import (
    EmbeddingBatch,
    EmbeddingProviderError,
)

from app.services.generation import (
    GenerationProviderError,
    GenerationResult,
)


client = TestClient(
    app
)


MANAGER_ID = UUID(
    "6b6b6b6b-6b6b-46b6-86b6-6b6b6b6b6b6b"
)


def fake_manager() -> InternalUser:

    return InternalUser(
        id=
            MANAGER_ID,

        email=
            "m6b-manager@test.local",

        name=
            "M6B Reliability Manager",

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

    vector[index] = 1.0

    return vector


def vector_literal(
    vector: list[float],
) -> str:

    return (
        "["
        + ",".join(
            str(value)
            for value
            in vector
        )
        + "]"
    )


@dataclass
class FakeEmbeddingProvider:

    provider_name: str = (
        "m6b-embedding"
    )

    model: str = (
        "m6b-embedding-v1"
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


class FailingEmbeddingProvider:

    provider_name = (
        "failing-embedding"
    )

    model = (
        "failing-embedding-v1"
    )

    dimensions = 1536


    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        raise EmbeddingProviderError(
            "synthetic embedding outage"
        )


    def embed(
        self,
        texts: list[str],
    ):

        raise AssertionError(
            "embed() should not be called"
        )


class WrongDimensionEmbeddingProvider:

    provider_name = (
        "wrong-dimension"
    )

    model = (
        "wrong-dimension-v1"
    )

    dimensions = 1536


    def embed_query(
        self,
        text: str,
    ) -> list[float]:

        return [
            0.0
            for _ in range(
                384
            )
        ]


    def embed(
        self,
        texts: list[str],
    ):

        raise AssertionError(
            "embed() should not be called"
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
                "Generation should not run "
                "for retrieval failures."
            )
        )


class FailingGenerationProvider:

    provider_name = (
        "failing-generation"
    )

    model = (
        "failing-generation-v1"
    )


    def generate_grounded(
        self,
        *,
        system_prompt: str,
        user_prompt: str,
    ):

        raise GenerationProviderError(
            "synthetic generation outage"
        )


class BadCitationGenerationProvider:

    provider_name = (
        "bad-grounding"
    )

    model = (
        "bad-grounding-v1"
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

                    answer=
                        "Synthetic unsupported answer.",

                    citation_refs=[
                        "K999",
                    ],
                ),

            input_tokens=
                1,

            output_tokens=
                1,

            generation_ms=
                1.0,
        )


def cleanup(
    *,
    ticket_id:
        str | None,

    source_id:
        str | None,
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


def create_ticket(
    body: str,
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
                "m6b-test@example.com",

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

                "suite":
                    "m6b",
            },
        },
    )

    assert (
        response.status_code
        == 201
    )

    payload = (
        response.json()
    )

    return (
        payload[
            "ticket_id"
        ],

        payload[
            "message_id"
        ],
    )


def create_high_evidence_source(
) -> str:

    source_response = client.post(
        "/api/v1/agent/knowledge/sources",

        json={
            "title":
                (
                    "M6B Reliability "
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
                        "Shipping",

                    "content":
                        (
                            "Standard shipping "
                            "takes 3 to 5 "
                            "business days."
                        ),

                    "metadata": {
                        "claim_key":
                            "shipping_window",
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
        source_response.json()[
            "id"
        ]
    )


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
                        repeat('c', 64),

                    index_fingerprint =
                        repeat('d', 64),

                    embedding_provider =
                        'm6b-embedding',

                    embedding_model =
                        'm6b-embedding-v1',

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


    return source_id


def assert_failed_run(
    *,
    ticket_id: str,
    message_id: str,

    expected_provider: str,
    expected_model: str,

    expected_error_code: str,
) -> None:

    with psycopg.connect(
        settings.database_url
    ) as connection:

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    provider,
                    model,
                    decision,
                    confidence_band,
                    error_code,
                    decision_reasons

                from public.ai_runs

                where message_id = %s

                order by created_at desc

                limit 1;
                """,
                (
                    message_id,
                ),
            )

            run = (
                cursor.fetchone()
            )

            assert run is not None

            assert run[0] == (
                expected_provider
            )

            assert run[1] == (
                expected_model
            )

            assert run[2] == "FAILED"

            assert run[3] == "LOW"

            assert run[4] == (
                expected_error_code
            )

            assert (
                expected_error_code
                in run[5]
            )

            assert (
                "AUTO_RESPONSE_BLOCKED"
                in run[5]
            )


            cursor.execute(
                """
                select
                    status,
                    confidence_band,
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
                "FAILED",
                "LOW",
                expected_error_code,
            )


            cursor.execute(
                """
                select count(*)::int

                from public.audit_events

                where entity_type =
                    'ai_run'

                  and event_type =
                    'SUPPORT_DECISION_EVALUATED'

                  and metadata ->> 'ticket_id'
                    = %s;
                """,
                (
                    ticket_id,
                ),
            )

            assert (
                cursor.fetchone()[0]
                == 1
            )


def install_route_dependencies(
    monkeypatch,
    *,
    embedding_provider,
    generation_provider,
) -> None:

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


def test_embedding_provider_failure_is_persisted(
    monkeypatch,
) -> None:

    install_route_dependencies(
        monkeypatch,

        embedding_provider=
            FailingEmbeddingProvider(),

        generation_provider=
            NeverCalledGenerationProvider(),
    )

    ticket_id = None

    try:

        ticket_id, message_id = (
            create_ticket(
                (
                    "How long does "
                    "standard shipping take?"
                )
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


        assert (
            response.status_code
            == 502
        )

        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            == "AI_PROVIDER_ERROR"
        )


        assert_failed_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,

            expected_provider=
                "failing-embedding",

            expected_model=
                "failing-embedding-v1",

            expected_error_code=
                "EMBEDDING_PROVIDER_ERROR",
        )

    finally:

        app.dependency_overrides.clear()

        cleanup(
            ticket_id=
                ticket_id,

            source_id=
                None,
        )


def test_retrieval_contract_failure_is_persisted(
    monkeypatch,
) -> None:

    install_route_dependencies(
        monkeypatch,

        embedding_provider=
            WrongDimensionEmbeddingProvider(),

        generation_provider=
            NeverCalledGenerationProvider(),
    )

    ticket_id = None

    try:

        ticket_id, message_id = (
            create_ticket(
                (
                    "How long does "
                    "standard shipping take?"
                )
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


        assert (
            response.status_code
            == 409
        )

        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            == "AI_GROUNDING_ERROR"
        )


        assert_failed_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,

            expected_provider=
                "wrong-dimension",

            expected_model=
                "wrong-dimension-v1",

            expected_error_code=
                (
                    "KNOWLEDGE_RETRIEVAL_"
                    "CONSISTENCY_ERROR"
                ),
        )

    finally:

        app.dependency_overrides.clear()

        cleanup(
            ticket_id=
                ticket_id,

            source_id=
                None,
        )


def test_generation_provider_failure_persists_evidence(
    monkeypatch,
) -> None:

    install_route_dependencies(
        monkeypatch,

        embedding_provider=
            FakeEmbeddingProvider(),

        generation_provider=
            FailingGenerationProvider(),
    )

    source_id = None
    ticket_id = None

    try:

        source_id = (
            create_high_evidence_source()
        )

        ticket_id, message_id = (
            create_ticket(
                (
                    "How long does "
                    "standard shipping take?"
                )
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


        assert (
            response.status_code
            == 502
        )

        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            == "AI_PROVIDER_ERROR"
        )


        assert_failed_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,

            expected_provider=
                "failing-generation",

            expected_model=
                "failing-generation-v1",

            expected_error_code=
                "GENERATION_PROVIDER_ERROR",
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select count(*)::int

                    from public.retrieval_evidence re

                    join public.ai_runs ar
                        on ar.id =
                            re.ai_run_id

                    where ar.message_id = %s;
                    """,
                    (
                        message_id,
                    ),
                )

                assert (
                    cursor.fetchone()[0]
                    >= 1
                )

    finally:

        app.dependency_overrides.clear()

        cleanup(
            ticket_id=
                ticket_id,

            source_id=
                source_id,
        )


def test_grounding_contract_failure_persists_evidence(
    monkeypatch,
) -> None:

    install_route_dependencies(
        monkeypatch,

        embedding_provider=
            FakeEmbeddingProvider(),

        generation_provider=
            BadCitationGenerationProvider(),
    )

    source_id = None
    ticket_id = None

    try:

        source_id = (
            create_high_evidence_source()
        )

        ticket_id, message_id = (
            create_ticket(
                (
                    "How long does "
                    "standard shipping take?"
                )
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


        assert (
            response.status_code
            == 409
        )

        assert (
            response.json()[
                "detail"
            ][
                "code"
            ]
            == "AI_GROUNDING_ERROR"
        )


        assert_failed_run(
            ticket_id=
                ticket_id,

            message_id=
                message_id,

            expected_provider=
                "bad-grounding",

            expected_model=
                "bad-grounding-v1",

            expected_error_code=
                "GROUNDING_CONSISTENCY_ERROR",
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:

            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    select count(*)::int

                    from public.retrieval_evidence re

                    join public.ai_runs ar
                        on ar.id =
                            re.ai_run_id

                    where ar.message_id = %s;
                    """,
                    (
                        message_id,
                    ),
                )

                assert (
                    cursor.fetchone()[0]
                    >= 1
                )

    finally:

        app.dependency_overrides.clear()

        cleanup(
            ticket_id=
                ticket_id,

            source_id=
                source_id,
        )
