from dataclasses import dataclass
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

from app.services.embeddings import (
    EmbeddingBatch,
)


client = TestClient(app)


MANAGER_ID = UUID(
    "44444444-4444-4444-8444-444444444444"
)


def fake_manager() -> InternalUser:
    return InternalUser(
        id=MANAGER_ID,
        email="index-manager@test.local",
        name="Index Test Manager",
        role="SUPPORT_MANAGER",
    )


@dataclass
class FakeEmbeddingProvider:
    provider_name: str = "test"
    model: str = "deterministic-test-v1"
    dimensions: int = 1536
    calls: int = 0


    def embed(
        self,
        texts: list[str],
    ) -> EmbeddingBatch:
        self.calls += 1

        vectors: list[
            list[float]
        ] = []

        for position, text in enumerate(
            texts,
            start=1,
        ):
            vector = [
                0.0
                for _ in range(
                    self.dimensions
                )
            ]

            vector[
                position
                % self.dimensions
            ] = 1.0

            vector[
                (
                    len(text)
                    + position
                )
                % self.dimensions
            ] = 0.5

            vectors.append(
                vector
            )

        return EmbeddingBatch(
            vectors=vectors,
            prompt_tokens=0,
        )


def cleanup_source(
    source_id: str,
) -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
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


def test_only_published_sources_can_be_indexed(
    monkeypatch,
) -> None:
    provider = (
        FakeEmbeddingProvider()
    )

    monkeypatch.setattr(
        (
            "app.api.routes.knowledge_index"
            ".get_embedding_provider"
        ),
        lambda: provider,
    )

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    source_id: str | None = None


    try:
        created = client.post(
            "/api/v1/agent/knowledge/sources",
            json={
                "title":
                    (
                        "Index State Test "
                        + str(uuid4())
                    ),

                "type":
                    "FAQ",

                "version":
                    "1.0",

                "sections": [
                    {
                        "section":
                            "Answer",

                        "content":
                            "Approved test content.",
                    }
                ],
            },
        )

        assert (
            created.status_code
            == 201
        )

        source_id = (
            created.json()["id"]
        )


        indexed = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/index"
            )
        )

        assert (
            indexed.status_code
            == 409
        )

        assert (
            provider.calls
            == 0
        )

    finally:
        app.dependency_overrides.clear()

        if source_id:
            cleanup_source(
                source_id
            )


def test_published_index_is_deterministic_and_idempotent(
    monkeypatch,
) -> None:
    provider = (
        FakeEmbeddingProvider()
    )

    monkeypatch.setattr(
        (
            "app.api.routes.knowledge_index"
            ".get_embedding_provider"
        ),
        lambda: provider,
    )

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    source_id: str | None = None


    try:
        created = client.post(
            "/api/v1/agent/knowledge/sources",
            json={
                "title":
                    (
                        "Deterministic Index Test "
                        + str(uuid4())
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
                                "Unused items may be returned "
                                "within 30 days."
                            ),
                    },
                    {
                        "section":
                            "Condition",

                        "content":
                            (
                                "Returned products must "
                                "remain unused."
                            ),
                    },
                ],

                "metadata": {
                    "test":
                        True,
                },
            },
        )

        assert (
            created.status_code
            == 201
        )

        source_id = (
            created.json()["id"]
        )


        published = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/publish"
            )
        )

        assert (
            published.status_code
            == 200
        )


        first_index = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/index"
            )
        )

        assert (
            first_index.status_code
            == 200
        )

        first_result = (
            first_index.json()
        )

        assert (
            first_result[
                "total_chunks"
            ]
            == 2
        )

        assert (
            first_result[
                "embedded_chunks"
            ]
            == 2
        )

        assert (
            first_result[
                "skipped_chunks"
            ]
            == 0
        )

        assert (
            provider.calls
            == 1
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                        count(*)::int,

                        count(
                            embedding
                        )::int,

                        min(
                            extensions.vector_dims(
                                embedding
                            )
                        ),

                        count(
                            distinct
                            index_fingerprint
                        )::int

                    from public.knowledge_chunks

                    where source_id = %s;
                    """,
                    (
                        source_id,
                    ),
                )

                row = (
                    cursor.fetchone()
                )


        assert row == (
            2,
            2,
            1536,
            2,
        )


        second_index = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + source_id
                + "/index"
            )
        )

        assert (
            second_index.status_code
            == 200
        )

        second_result = (
            second_index.json()
        )

        assert (
            second_result[
                "embedded_chunks"
            ]
            == 0
        )

        assert (
            second_result[
                "skipped_chunks"
            ]
            == 2
        )

        # No second external provider call.
        assert (
            provider.calls
            == 1
        )


        with psycopg.connect(
            settings.database_url
        ) as connection:
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select count(*)::int

                    from public.audit_events

                    where entity_type =
                        'knowledge_source'

                      and entity_id = %s

                      and event_type =
                        'KNOWLEDGE_SOURCE_INDEXED';
                    """,
                    (
                        source_id,
                    ),
                )

                index_events = (
                    cursor.fetchone()[0]
                )


        # Only the run that actually generated vectors
        # creates an indexing audit event.
        assert (
            index_events
            == 1
        )

    finally:
        app.dependency_overrides.clear()

        if source_id:
            cleanup_source(
                source_id
            )