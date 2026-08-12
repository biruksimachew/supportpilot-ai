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


client = TestClient(app)


MANAGER_ID = UUID(
    "55555555-5555-4555-8555-555555555555"
)


def fake_manager() -> InternalUser:
    return InternalUser(
        id=MANAGER_ID,
        email="retrieval-manager@test.local",
        name="Retrieval Test Manager",
        role="SUPPORT_MANAGER",
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
class FakeRetrievalProvider:
    provider_name: str = (
        "retrieval-test"
    )

    model: str = (
        "semantic-test-v1"
    )

    dimensions: int = 1536


    def embed_query(
        self,
        text: str,
    ) -> list[float]:
        if "return" in text.lower():
            return basis_vector(
                0
            )

        if (
            "shipping"
            in text.lower()
        ):
            return basis_vector(
                1
            )

        return basis_vector(
            2
        )


    def embed(
        self,
        texts: list[str],
    ):
        raise AssertionError(
            (
                "Retrieval must use "
                "embed_query(), not embed()."
            )
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


def set_chunk_embedding(
    *,
    source_id: str,
    section: str,
    vector: list[float],
) -> None:
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
                        'retrieval-test',

                    embedding_model =
                        'semantic-test-v1',

                    embedding_dimensions =
                        1536,

                    embedded_at =
                        now()

                where source_id = %s
                  and section = %s;
                """,
                (
                    vector_literal(
                        vector
                    ),

                    source_id,
                    section,
                ),
            )

            assert (
                cursor.rowcount
                == 1
            )


def create_source(
    *,
    title: str,
) -> str:
    response = client.post(
        "/api/v1/agent/knowledge/sources",
        json={
            "title":
                title,

            "type":
                "POLICY",

            "version":
                "1.0",

            "sections": [
                {
                    "section":
                        "Returns",

                    "content":
                        (
                            "Unused items may be "
                            "returned within "
                            "30 calendar days."
                        ),
                },
                {
                    "section":
                        "Shipping",

                    "content":
                        (
                            "Standard shipping "
                            "normally arrives "
                            "within five to "
                            "seven business days."
                        ),
                },
            ],
        },
    )

    assert (
        response.status_code
        == 201
    )

    return response.json()[
        "id"
    ]


def test_retrieval_ranks_semantic_match_and_excludes_draft(
    monkeypatch,
) -> None:
    provider = (
        FakeRetrievalProvider()
    )

    monkeypatch.setattr(
        (
            "app.api.routes."
            "knowledge_retrieval."
            "get_embedding_provider"
        ),
        lambda: provider,
    )

    app.dependency_overrides[
        get_current_internal_user
    ] = fake_manager


    published_id: str | None = None
    draft_id: str | None = None


    try:
        published_id = (
            create_source(
                title=(
                    "Published Retrieval Test "
                    + str(uuid4())
                )
            )
        )


        published = client.post(
            (
                "/api/v1/agent/knowledge/sources/"
                + published_id
                + "/publish"
            )
        )

        assert (
            published.status_code
            == 200
        )


        set_chunk_embedding(
            source_id=
                published_id,

            section=
                "Returns",

            vector=
                basis_vector(0),
        )

        set_chunk_embedding(
            source_id=
                published_id,

            section=
                "Shipping",

            vector=
                basis_vector(1),
        )


        # --------------------------------------------------
        # Simulate stale vectors on a DRAFT source.
        # Retrieval must still never return it.
        # --------------------------------------------------

        draft_id = (
            create_source(
                title=(
                    "Draft Retrieval Test "
                    + str(uuid4())
                )
            )
        )


        set_chunk_embedding(
            source_id=
                draft_id,

            section=
                "Returns",

            vector=
                basis_vector(0),
        )


        response = client.post(
            "/api/v1/agent/knowledge/retrieve",
            json={
                "question":
                    (
                        "Can I return an "
                        "unused item?"
                    ),

                "top_k":
                    5,

                "min_similarity":
                    0.0,
            },
        )


        assert (
            response.status_code
            == 200
        )


        result = (
            response.json()
        )


        assert (
            result["provider"]
            == "retrieval-test"
        )

        assert (
            result["model"]
            == "semantic-test-v1"
        )

        assert (
            result["dimensions"]
            == 1536
        )


        results = (
            result["results"]
        )


        assert len(
            results
        ) >= 1


        assert (
            results[0][
                "source_id"
            ]
            == published_id
        )

        assert (
            results[0][
                "section"
            ]
            == "Returns"
        )

        assert (
            results[0][
                "similarity"
            ]
            == 1.0
        )


        returned_source_ids = {
            item[
                "source_id"
            ]
            for item
            in results
        }


        assert (
            draft_id
            not in returned_source_ids
        )


    finally:
        app.dependency_overrides.clear()

        if published_id:
            cleanup_source(
                published_id
            )

        if draft_id:
            cleanup_source(
                draft_id
            )


def test_knowledge_retrieval_requires_authentication():
    app.dependency_overrides.clear()

    response = client.post(
        "/api/v1/agent/knowledge/retrieve",
        json={
            "question":
                "What is the return policy?"
        },
    )

    assert (
        response.status_code
        == 401
    )