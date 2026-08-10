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

from app.schemas.knowledge import (
    KnowledgeRetireRequest,
    KnowledgeSection,
    KnowledgeSectionInput,
    KnowledgeSourceCreate,
    KnowledgeSourceDetail,
    KnowledgeSourceListResponse,
    KnowledgeSourceStatus,
    KnowledgeSourceSummary,
    KnowledgeSourceType,
    KnowledgeSourceUpdate,
)


class KnowledgeSourceNotFoundError(
    LookupError
):
    pass


class KnowledgeSourceStateError(
    ValueError
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

    return mapping[user.role]


def _normalize_sections(
    sections: list[
        KnowledgeSectionInput
    ],
) -> list[dict]:
    normalized: list[dict] = []

    for index, section in enumerate(
        sections,
        start=1,
    ):
        normalized.append(
            {
                "section":
                    section.section.strip(),

                "content":
                    section.content.strip(),

                "metadata": {
                    **section.metadata,
                    "ordinal": index,
                },
            }
        )

    return normalized


def _checksum_payload(
    *,
    title: str,
    source_type: str,
    version: str,
    effective_at: datetime | None,
    sections: list[dict],
) -> str:
    effective_value = None

    if effective_at is not None:
        effective_value = (
            effective_at
            .astimezone(
                timezone.utc
            )
            .isoformat()
        )

    payload = {
        "title":
            title.strip(),

        "type":
            source_type,

        "version":
            version.strip(),

        "effective_at":
            effective_value,

        "sections": [
            {
                "section":
                    section[
                        "section"
                    ],

                "content":
                    section[
                        "content"
                    ],

                "metadata":
                    section[
                        "metadata"
                    ],
            }
            for section
            in sections
        ],
    }

    canonical = json.dumps(
        payload,
        sort_keys=True,
        separators=(
            ",",
            ":",
        ),
        ensure_ascii=False,
    )

    return hashlib.sha256(
        canonical.encode(
            "utf-8"
        )
    ).hexdigest()


def _insert_audit_event(
    cursor,
    *,
    user: InternalUser,
    event_type: str,
    source_id: UUID,
    metadata: dict,
) -> None:
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
            %s,
            'knowledge_source',
            %s,
            %s
        );
        """,
        (
            _actor_type(user),
            str(user.id),
            event_type,
            str(source_id),
            Jsonb(metadata),
        ),
    )


def _load_source_detail(
    cursor,
    source_id: UUID,
    *,
    published_only: bool = False,
) -> KnowledgeSourceDetail | None:
    visibility_clause = ""

    if published_only:
        visibility_clause = (
            "and ks.status = 'PUBLISHED'"
        )

    cursor.execute(
        f"""
        select
            ks.id,
            ks.title,
            ks.type,
            ks.version,
            ks.status,
            ks.effective_at,
            ks.last_updated,
            ks.checksum,
            ks.created_by,
            ks.created_at,
            ks.retired_at,
            ks.metadata,

            (
                select count(*)
                from public.knowledge_chunks kc
                where kc.source_id = ks.id
            )::int
                as section_count

        from public.knowledge_sources ks

        where ks.id = %s
        {visibility_clause}

        limit 1;
        """,
        (
            source_id,
        ),
    )

    source = cursor.fetchone()

    if source is None:
        return None

    cursor.execute(
        """
        select
            id,
            section,
            content,
            metadata,
            created_at

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

    sections = [
        KnowledgeSection(
            **row
        )
        for row
        in cursor.fetchall()
    ]

    return KnowledgeSourceDetail(
        **source,
        sections=sections,
    )


def list_knowledge_sources(
    *,
    user: InternalUser,
    status: KnowledgeSourceStatus | None = None,
    source_type: KnowledgeSourceType | None = None,
) -> KnowledgeSourceListResponse:
    filters: list[str] = []
    parameters: list[object] = []

    if user.role == "SUPPORT_AGENT":
        filters.append(
            "ks.status = 'PUBLISHED'"
        )

    elif status is not None:
        filters.append(
            "ks.status = %s"
        )
        parameters.append(
            status
        )

    if source_type is not None:
        filters.append(
            "ks.type = %s"
        )
        parameters.append(
            source_type
        )

    where_clause = ""

    if filters:
        where_clause = (
            "where "
            + " and ".join(
                filters
            )
        )

    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                select
                    count(*)::int
                        as total

                from public.knowledge_sources ks

                {where_clause};
                """,
                tuple(
                    parameters
                ),
            )

            total = cursor.fetchone()[
                "total"
            ]

            cursor.execute(
                f"""
                select
                    ks.id,
                    ks.title,
                    ks.type,
                    ks.version,
                    ks.status,
                    ks.effective_at,
                    ks.last_updated,
                    ks.checksum,
                    ks.created_by,
                    ks.created_at,
                    ks.retired_at,
                    ks.metadata,

                    (
                        select count(*)
                        from public.knowledge_chunks kc
                        where kc.source_id = ks.id
                    )::int
                        as section_count

                from public.knowledge_sources ks

                {where_clause}

                order by
                    ks.last_updated desc,
                    ks.created_at desc,
                    ks.id;
                """,
                tuple(
                    parameters
                ),
            )

            items = [
                KnowledgeSourceSummary(
                    **row
                )
                for row
                in cursor.fetchall()
            ]

    return KnowledgeSourceListResponse(
        items=items,
        total=total,
    )


def get_knowledge_source(
    *,
    user: InternalUser,
    source_id: UUID,
) -> KnowledgeSourceDetail:
    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.cursor() as cursor:
            source = _load_source_detail(
                cursor,
                source_id,
                published_only=(
                    user.role
                    == "SUPPORT_AGENT"
                ),
            )

    if source is None:
        raise KnowledgeSourceNotFoundError(
            "Knowledge source not found."
        )

    return source


def create_knowledge_source(
    *,
    user: InternalUser,
    payload: KnowledgeSourceCreate,
) -> KnowledgeSourceDetail:
    title = payload.title.strip()
    version = payload.version.strip()

    sections = _normalize_sections(
        payload.sections
    )

    checksum = _checksum_payload(
        title=title,
        source_type=payload.type,
        version=version,
        effective_at=payload.effective_at,
        sections=sections,
    )

    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.transaction():
            with connection.cursor() as cursor:

                cursor.execute(
                    """
                    insert into public.knowledge_sources (
                        title,
                        type,
                        version,
                        status,
                        effective_at,
                        checksum,
                        created_by,
                        metadata
                    )
                    values (
                        %s,
                        %s,
                        %s,
                        'DRAFT',
                        %s,
                        %s,

                        case
                            when exists (
                                select 1
                                from public.users
                                where id = %s
                            )
                            then %s
                            else null
                        end,

                        %s
                    )
                    returning id;
                    """,
                    (
                        title,
                        payload.type,
                        version,
                        payload.effective_at,
                        checksum,
                        user.id,
                        user.id,
                        Jsonb(
                            payload.metadata
                        ),
                    ),
                )

                source_id = (
                    cursor.fetchone()[
                        "id"
                    ]
                )

                for section in sections:
                    cursor.execute(
                        """
                        insert into public.knowledge_chunks (
                            source_id,
                            section,
                            content,
                            embedding,
                            metadata
                        )
                        values (
                            %s,
                            %s,
                            %s,
                            null,
                            %s
                        );
                        """,
                        (
                            source_id,
                            section[
                                "section"
                            ],
                            section[
                                "content"
                            ],
                            Jsonb(
                                section[
                                    "metadata"
                                ]
                            ),
                        ),
                    )

                _insert_audit_event(
                    cursor,
                    user=user,
                    event_type=(
                        "KNOWLEDGE_SOURCE_CREATED"
                    ),
                    source_id=source_id,
                    metadata={
                        "title":
                            title,

                        "type":
                            payload.type,

                        "version":
                            version,

                        "status":
                            "DRAFT",

                        "checksum":
                            checksum,

                        "section_count":
                            len(
                                sections
                            ),
                    },
                )

                result = (
                    _load_source_detail(
                        cursor,
                        source_id,
                    )
                )

    assert result is not None

    return result


def update_knowledge_source(
    *,
    user: InternalUser,
    source_id: UUID,
    payload: KnowledgeSourceUpdate,
) -> KnowledgeSourceDetail:
    title = payload.title.strip()
    version = payload.version.strip()

    sections = _normalize_sections(
        payload.sections
    )

    checksum = _checksum_payload(
        title=title,
        source_type=payload.type,
        version=version,
        effective_at=payload.effective_at,
        sections=sections,
    )

    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.transaction():
            with connection.cursor() as cursor:
                cursor.execute(
                    """
                    select
                        id,
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

                existing = (
                    cursor.fetchone()
                )

                if existing is None:
                    raise (
                        KnowledgeSourceNotFoundError(
                            "Knowledge source not found."
                        )
                    )

                if (
                    existing["status"]
                    != "DRAFT"
                ):
                    raise (
                        KnowledgeSourceStateError(
                            "Only draft knowledge sources can be edited."
                        )
                    )

                previous_checksum = (
                    existing[
                        "checksum"
                    ]
                )

                cursor.execute(
                    """
                    update public.knowledge_sources
                    set
                        title = %s,
                        type = %s,
                        version = %s,
                        effective_at = %s,
                        checksum = %s,
                        metadata = %s

                    where id = %s;
                    """,
                    (
                        title,
                        payload.type,
                        version,
                        payload.effective_at,
                        checksum,
                        Jsonb(
                            payload.metadata
                        ),
                        source_id,
                    ),
                )

                cursor.execute(
                    """
                    delete
                    from public.knowledge_chunks
                    where source_id = %s;
                    """,
                    (
                        source_id,
                    ),
                )

                for section in sections:
                    cursor.execute(
                        """
                        insert into public.knowledge_chunks (
                            source_id,
                            section,
                            content,
                            embedding,
                            metadata
                        )
                        values (
                            %s,
                            %s,
                            %s,
                            null,
                            %s
                        );
                        """,
                        (
                            source_id,
                            section[
                                "section"
                            ],
                            section[
                                "content"
                            ],
                            Jsonb(
                                section[
                                    "metadata"
                                ]
                            ),
                        ),
                    )

                _insert_audit_event(
                    cursor,
                    user=user,
                    event_type=(
                        "KNOWLEDGE_SOURCE_UPDATED"
                    ),
                    source_id=source_id,
                    metadata={
                        "title":
                            title,

                        "type":
                            payload.type,

                        "version":
                            version,

                        "previous_checksum":
                            previous_checksum,

                        "checksum":
                            checksum,

                        "section_count":
                            len(
                                sections
                            ),
                    },
                )

                result = (
                    _load_source_detail(
                        cursor,
                        source_id,
                    )
                )

    assert result is not None

    return result


def publish_knowledge_source(
    *,
    user: InternalUser,
    source_id: UUID,
) -> KnowledgeSourceDetail:
    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.transaction():
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

                    for update;
                    """,
                    (
                        source_id,
                    ),
                )

                existing = (
                    cursor.fetchone()
                )

                if existing is None:
                    raise (
                        KnowledgeSourceNotFoundError(
                            "Knowledge source not found."
                        )
                    )

                if (
                    existing["status"]
                    != "DRAFT"
                ):
                    raise (
                        KnowledgeSourceStateError(
                            "Only draft knowledge sources can be published."
                        )
                    )

                cursor.execute(
                    """
                    select count(*)::int
                        as section_count

                    from public.knowledge_chunks

                    where source_id = %s;
                    """,
                    (
                        source_id,
                    ),
                )

                section_count = (
                    cursor.fetchone()[
                        "section_count"
                    ]
                )

                if section_count < 1:
                    raise (
                        KnowledgeSourceStateError(
                            "Knowledge source must contain at least one section before publishing."
                        )
                    )

                cursor.execute(
                    """
                    update public.knowledge_sources
                    set
                        status = 'PUBLISHED',

                        effective_at =
                            coalesce(
                                effective_at,
                                now()
                            ),

                        retired_at = null

                    where id = %s;
                    """,
                    (
                        source_id,
                    ),
                )

                _insert_audit_event(
                    cursor,
                    user=user,
                    event_type=(
                        "KNOWLEDGE_SOURCE_PUBLISHED"
                    ),
                    source_id=source_id,
                    metadata={
                        "title":
                            existing[
                                "title"
                            ],

                        "type":
                            existing[
                                "type"
                            ],

                        "version":
                            existing[
                                "version"
                            ],

                        "checksum":
                            existing[
                                "checksum"
                            ],

                        "section_count":
                            section_count,
                    },
                )

                result = (
                    _load_source_detail(
                        cursor,
                        source_id,
                    )
                )

    assert result is not None

    return result


def retire_knowledge_source(
    *,
    user: InternalUser,
    source_id: UUID,
    payload: KnowledgeRetireRequest,
) -> KnowledgeSourceDetail:
    with get_database_connection() as connection:
        connection.row_factory = (
            dict_row
        )

        with connection.transaction():
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

                    for update;
                    """,
                    (
                        source_id,
                    ),
                )

                existing = (
                    cursor.fetchone()
                )

                if existing is None:
                    raise (
                        KnowledgeSourceNotFoundError(
                            "Knowledge source not found."
                        )
                    )

                if (
                    existing["status"]
                    != "PUBLISHED"
                ):
                    raise (
                        KnowledgeSourceStateError(
                            "Only published knowledge sources can be retired."
                        )
                    )

                cursor.execute(
                    """
                    update public.knowledge_sources
                    set
                        status = 'RETIRED',
                        retired_at = now()

                    where id = %s;
                    """,
                    (
                        source_id,
                    ),
                )

                _insert_audit_event(
                    cursor,
                    user=user,
                    event_type=(
                        "KNOWLEDGE_SOURCE_RETIRED"
                    ),
                    source_id=source_id,
                    metadata={
                        "title":
                            existing[
                                "title"
                            ],

                        "type":
                            existing[
                                "type"
                            ],

                        "version":
                            existing[
                                "version"
                            ],

                        "checksum":
                            existing[
                                "checksum"
                            ],

                        "reason":
                            payload.reason.strip(),
                    },
                )

                result = (
                    _load_source_detail(
                        cursor,
                        source_id,
                    )
                )

    assert result is not None

    return result