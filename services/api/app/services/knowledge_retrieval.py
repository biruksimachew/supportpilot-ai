import math

from psycopg.rows import dict_row

from app.core.database import (
    get_database_connection,
)

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalResponse,
    KnowledgeRetrievalResult,
)

from app.services.embeddings import (
    EmbeddingProvider,
    EmbeddingProviderError,
)


class KnowledgeRetrievalConsistencyError(
    RuntimeError
):
    pass


def _vector_literal(
    vector: list[float],
) -> str:
    return (
        "["
        + ",".join(
            repr(
                float(value)
            )
            for value
            in vector
        )
        + "]"
    )


def retrieve_knowledge(
    *,
    question: str,
    provider: EmbeddingProvider,
    top_k: int = 5,
    min_similarity: float = 0.0,
) -> KnowledgeRetrievalResponse:
    normalized_question = (
        question.strip()
    )

    if not normalized_question:
        raise ValueError(
            "Question must not be empty."
        )


    query_vector = (
        provider.embed_query(
            normalized_question
        )
    )


    if (
        len(query_vector)
        != provider.dimensions
    ):
        raise (
            KnowledgeRetrievalConsistencyError(
                (
                    "Query embedding dimension "
                    "does not match provider "
                    "configuration."
                )
            )
        )


    if provider.dimensions != 1536:
        raise (
            KnowledgeRetrievalConsistencyError(
                (
                    "SupportPilot knowledge retrieval "
                    "requires 1536-dimensional vectors."
                )
            )
        )


    if not all(
        math.isfinite(
            value
        )
        for value
        in query_vector
    ):
        raise EmbeddingProviderError(
            (
                "Query embedding contains "
                "non-finite values."
            )
        )


    vector_literal = (
        _vector_literal(
            query_vector
        )
    )


    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                with query_embedding as (
                    select
                        %s::extensions.vector
                            as embedding
                ),

                ranked as (
                    select
                        kc.id
                            as chunk_id,

                        ks.id
                            as source_id,

                        ks.title,
                        ks.type,
                        ks.version,

                        kc.section,
                        kc.content,

                        (
                            1
                            -
                            (
                                kc.embedding
                                <=>
                                query_embedding.embedding
                            )
                        )::double precision
                            as similarity,

                        ks.effective_at,

                        ks.metadata
                            as source_metadata,

                        kc.metadata
                            as chunk_metadata

                    from public.knowledge_chunks kc

                    join public.knowledge_sources ks
                        on ks.id =
                            kc.source_id

                    cross join query_embedding

                    where
                        ks.status =
                            'PUBLISHED'

                        and ks.effective_at
                            <= now()

                        and kc.embedding
                            is not null

                        and kc.embedding_provider
                            = %s

                        and kc.embedding_model
                            = %s

                        and kc.embedding_dimensions
                            = %s
                )

                select
                    chunk_id,
                    source_id,

                    title,
                    type,
                    version,

                    section,
                    content,

                    similarity,

                    effective_at,

                    source_metadata,
                    chunk_metadata

                from ranked

                where similarity >= %s

                order by
                    similarity desc,
                    title,
                    source_id,
                    chunk_id

                limit %s;
                """,
                (
                    vector_literal,

                    provider.provider_name,
                    provider.model,
                    provider.dimensions,

                    min_similarity,
                    top_k,
                ),
            )

            rows = (
                cursor.fetchall()
            )


    results = [
        KnowledgeRetrievalResult(
            **row
        )
        for row
        in rows
    ]


    return KnowledgeRetrievalResponse(
        question=
            normalized_question,

        provider=
            provider.provider_name,

        model=
            provider.model,

        dimensions=
            provider.dimensions,

        top_k=
            top_k,

        min_similarity=
            min_similarity,

        results=
            results,
    )