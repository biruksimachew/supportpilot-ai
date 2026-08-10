import hashlib
import json

from datetime import (
    datetime,
    timezone,
)

from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.knowledge_index import (
    KnowledgeIndexResponse,
)

from app.services.embeddings import (
    EmbeddingProvider,
)

from app.services.knowledge import (
    KnowledgeSourceNotFoundError,
)


class KnowledgeIndexStateError(
    ValueError
):
    pass


class KnowledgeIndexConsistencyError(
    RuntimeError
):
    pass


def _actor_type(
    user: InternalUser,
) -> str:
    mapping = {
        "SUPPORT_AGENT":
            "AGENT",

        "SUPPORT_MANAGER":
            "MANAGER",

        "SYSTEM_ADMIN":
            "ADMIN",
    }

    return mapping[
        user.role
    ]


def _sha256(
    value: str,
) -> str:
    return hashlib.sha256(
        value.encode(
            "utf-8"
        )
    ).hexdigest()


def _embedding_text(
    *,
    source: dict,
    chunk: dict,
) -> str:
    section = (
        chunk["section"]
        or "General"
    ).strip()

    content = (
        chunk["content"]
        .strip()
    )

    return "\n".join(
        [
            (
                "Knowledge title: "
                + source["title"].strip()
            ),
            (
                "Knowledge type: "
                + source["type"]
            ),
            (
                "Knowledge version: "
                + source["version"].strip()
            ),
            (
                "Section: "
                + section
            ),
            "",
            content,
        ]
    )


def _index_fingerprint(
    *,
    text: str,
    provider: EmbeddingProvider,
) -> str:
    canonical = json.dumps(
        {
            "provider":
                provider.provider_name,

            "model":
                provider.model,

            "dimensions":
                provider.dimensions,

            "embedding_text":
                text,
        },
        ensure_ascii=False,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
    )

    return _sha256(
        canonical
    )


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


def index_knowledge_source(
    *,
    user: InternalUser,
    source_id: UUID,
    provider: EmbeddingProvider,
    force: bool = False,
) -> KnowledgeIndexResponse:
    if provider.dimensions != 1536:
        raise KnowledgeIndexConsistencyError(
            (
                "SupportPilot knowledge vectors "
                "must contain 1536 dimensions."
            )
        )


    # --------------------------------------------------------
    # Phase 1:
    # Snapshot immutable published content before network I/O.
    # --------------------------------------------------------

    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    id,
                    title,
                    type,
                    version,
                    status,
                    checksum

                from public.knowledge_sources

                where id = %s

                limit 1;
                """,
                (
                    source_id,
                ),
            )

            source = (
                cursor.fetchone()
            )


            if source is None:
                raise (
                    KnowledgeSourceNotFoundError(
                        "Knowledge source not found."
                    )
                )


            if (
                source["status"]
                != "PUBLISHED"
            ):
                raise (
                    KnowledgeIndexStateError(
                        (
                            "Only published knowledge "
                            "sources can be indexed."
                        )
                    )
                )


            cursor.execute(
                """
                select
                    id,
                    section,
                    content,
                    metadata,

                    (
                        embedding
                        is not null
                    ) as has_embedding,

                    content_checksum,
                    index_fingerprint,
                    embedding_provider,
                    embedding_model,
                    embedding_dimensions

                from public.knowledge_chunks

                where source_id = %s

                order by
                    case
                        when (
                            metadata ->> 'ordinal'
                        ) ~ '^[0-9]+$'
                        then (
                            metadata ->> 'ordinal'
                        )::int

                        else 2147483647
                    end,
                    created_at,
                    id;
                """,
                (
                    source_id,
                ),
            )

            chunks = (
                cursor.fetchall()
            )


    if not chunks:
        raise KnowledgeIndexStateError(
            (
                "Published knowledge source "
                "contains no chunks."
            )
        )


    prepared: list[dict] = []


    for chunk in chunks:
        text = _embedding_text(
            source=source,
            chunk=chunk,
        )

        content_checksum = (
            _sha256(
                chunk[
                    "content"
                ].strip()
            )
        )

        fingerprint = (
            _index_fingerprint(
                text=text,
                provider=provider,
            )
        )


        unchanged = (
            chunk[
                "has_embedding"
            ]

            and chunk[
                "content_checksum"
            ]
            == content_checksum

            and chunk[
                "index_fingerprint"
            ]
            == fingerprint

            and chunk[
                "embedding_provider"
            ]
            == provider.provider_name

            and chunk[
                "embedding_model"
            ]
            == provider.model

            and chunk[
                "embedding_dimensions"
            ]
            == provider.dimensions
        )


        prepared.append(
            {
                "id":
                    chunk["id"],

                "text":
                    text,

                "content_checksum":
                    content_checksum,

                "index_fingerprint":
                    fingerprint,

                "needs_embedding":
                    (
                        force
                        or not unchanged
                    ),
            }
        )


    pending = [
        item
        for item
        in prepared
        if item[
            "needs_embedding"
        ]
    ]


    now = datetime.now(
        timezone.utc
    )


    if not pending:
        return KnowledgeIndexResponse(
            source_id=source_id,
            source_status="PUBLISHED",

            provider=
                provider.provider_name,

            model=
                provider.model,

            dimensions=
                provider.dimensions,

            total_chunks=
                len(prepared),

            embedded_chunks=0,

            skipped_chunks=
                len(prepared),

            prompt_tokens=0,

            indexed_at=now,
        )


    # --------------------------------------------------------
    # Phase 2:
    # External provider call.
    #
    # No database transaction is intentionally held open while
    # waiting on the network.
    # --------------------------------------------------------

    embedding_batch = (
        provider.embed(
            [
                item["text"]
                for item
                in pending
            ]
        )
    )


    if (
        len(
            embedding_batch.vectors
        )
        != len(pending)
    ):
        raise KnowledgeIndexConsistencyError(
            (
                "Embedding provider returned "
                "an unexpected vector count."
            )
        )


    # --------------------------------------------------------
    # Phase 3:
    # Re-check lifecycle, then persist vectors atomically.
    # --------------------------------------------------------

    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                        status,
                        checksum

                    from public.knowledge_sources

                    where id = %s

                    for update;
                    """,
                    (
                        source_id,
                    ),
                )

                locked_source = (
                    cursor.fetchone()
                )


                if locked_source is None:
                    raise (
                        KnowledgeSourceNotFoundError(
                            "Knowledge source not found."
                        )
                    )


                if (
                    locked_source["status"]
                    != "PUBLISHED"
                ):
                    raise (
                        KnowledgeIndexStateError(
                            (
                                "Knowledge source changed "
                                "state during indexing."
                            )
                        )
                    )


                if (
                    locked_source["checksum"]
                    != source["checksum"]
                ):
                    raise (
                        KnowledgeIndexConsistencyError(
                            (
                                "Knowledge source changed "
                                "during indexing."
                            )
                        )
                    )


                for item, vector in zip(
                    pending,
                    embedding_batch.vectors,
                    strict=True,
                ):
                    if (
                        len(vector)
                        != provider.dimensions
                    ):
                        raise (
                            KnowledgeIndexConsistencyError(
                                (
                                    "Embedding dimension "
                                    "mismatch."
                                )
                            )
                        )


                    cursor.execute(
                        """
                        update public.knowledge_chunks
                        set
                            embedding =
                                %s::extensions.vector,

                            content_checksum =
                                %s,

                            index_fingerprint =
                                %s,

                            embedding_provider =
                                %s,

                            embedding_model =
                                %s,

                            embedding_dimensions =
                                %s,

                            embedded_at =
                                %s

                        where id = %s
                          and source_id = %s;
                        """,
                        (
                            _vector_literal(
                                vector
                            ),

                            item[
                                "content_checksum"
                            ],

                            item[
                                "index_fingerprint"
                            ],

                            provider.provider_name,

                            provider.model,

                            provider.dimensions,

                            now,

                            item["id"],

                            source_id,
                        ),
                    )


                    if cursor.rowcount != 1:
                        raise (
                            KnowledgeIndexConsistencyError(
                                (
                                    "Knowledge chunk changed "
                                    "during indexing."
                                )
                            )
                        )


                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,
                        event_type,
                        entity_type,
                        entity_id,
                        metadata
                    )
                    values (
                        %s,
                        %s,
                        'KNOWLEDGE_SOURCE_INDEXED',
                        'knowledge_source',
                        %s,
                        %s
                    );
                    """,
                    (
                        _actor_type(
                            user
                        ),

                        str(
                            user.id
                        ),

                        str(
                            source_id
                        ),

                        Jsonb(
                            {
                                "provider":
                                    provider.provider_name,

                                "model":
                                    provider.model,

                                "dimensions":
                                    provider.dimensions,

                                "total_chunks":
                                    len(
                                        prepared
                                    ),

                                "embedded_chunks":
                                    len(
                                        pending
                                    ),

                                "skipped_chunks":
                                    (
                                        len(prepared)
                                        - len(pending)
                                    ),

                                "prompt_tokens":
                                    (
                                        embedding_batch
                                        .prompt_tokens
                                    ),

                                "force":
                                    force,
                            }
                        ),
                    ),
                )


    return KnowledgeIndexResponse(
        source_id=source_id,
        source_status="PUBLISHED",

        provider=
            provider.provider_name,

        model=
            provider.model,

        dimensions=
            provider.dimensions,

        total_chunks=
            len(prepared),

        embedded_chunks=
            len(pending),

        skipped_chunks=
            (
                len(prepared)
                - len(pending)
            ),

        prompt_tokens=
            embedding_batch.prompt_tokens,

        indexed_at=now,
    )