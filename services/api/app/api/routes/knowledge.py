from uuid import UUID

import psycopg

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.core.auth import (
    get_current_internal_user,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.knowledge import (
    KnowledgeRetireRequest,
    KnowledgeSourceCreate,
    KnowledgeSourceDetail,
    KnowledgeSourceListResponse,
    KnowledgeSourceStatus,
    KnowledgeSourceType,
    KnowledgeSourceUpdate,
)

from app.services.knowledge import (
    KnowledgeSourceNotFoundError,
    KnowledgeSourceStateError,
    create_knowledge_source,
    get_knowledge_source,
    list_knowledge_sources,
    publish_knowledge_source,
    retire_knowledge_source,
    update_knowledge_source,
)


router = APIRouter(
    prefix="/api/v1/agent/knowledge",
    tags=["knowledge"],
)


def require_knowledge_manager(
    user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> InternalUser:
    if user.role not in (
        "SUPPORT_MANAGER",
        "SYSTEM_ADMIN",
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code":
                    "KNOWLEDGE_MANAGEMENT_FORBIDDEN",

                "message":
                    (
                        "Manager or administrator "
                        "access is required."
                    ),
            },
        )

    return user


@router.get(
    "/sources",
    response_model=
        KnowledgeSourceListResponse,
)
def read_knowledge_sources(
    source_status:
        KnowledgeSourceStatus | None
        = Query(
            default=None,
            alias="status",
        ),

    source_type:
        KnowledgeSourceType | None
        = Query(
            default=None,
            alias="type",
        ),

    user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> KnowledgeSourceListResponse:
    try:
        return list_knowledge_sources(
            user=user,
            status=source_status,
            source_type=source_type,
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_UNAVAILABLE",

                "message":
                    (
                        "Knowledge sources are "
                        "temporarily unavailable."
                    ),
            },
        ) from exc


@router.get(
    "/sources/{source_id}",
    response_model=
        KnowledgeSourceDetail,
)
def read_knowledge_source(
    source_id: UUID,

    user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> KnowledgeSourceDetail:
    try:
        return get_knowledge_source(
            user=user,
            source_id=source_id,
        )

    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "KNOWLEDGE_SOURCE_NOT_FOUND",

                "message":
                    "Knowledge source not found.",
            },
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_UNAVAILABLE",

                "message":
                    (
                        "Knowledge source is "
                        "temporarily unavailable."
                    ),
            },
        ) from exc


@router.post(
    "/sources",
    response_model=
        KnowledgeSourceDetail,
    status_code=
        status.HTTP_201_CREATED,
)
def create_source(
    payload: KnowledgeSourceCreate,

    user: InternalUser = Depends(
        require_knowledge_manager
    ),
) -> KnowledgeSourceDetail:
    try:
        return create_knowledge_source(
            user=user,
            payload=payload,
        )

    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "KNOWLEDGE_VERSION_EXISTS",

                "message":
                    (
                        "A knowledge source with "
                        "this title and version "
                        "already exists."
                    ),
            },
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_CREATE_UNAVAILABLE",

                "message":
                    (
                        "The knowledge source "
                        "could not be created."
                    ),
            },
        ) from exc


@router.put(
    "/sources/{source_id}",
    response_model=
        KnowledgeSourceDetail,
)
def replace_draft_source(
    source_id: UUID,
    payload: KnowledgeSourceUpdate,

    user: InternalUser = Depends(
        require_knowledge_manager
    ),
) -> KnowledgeSourceDetail:
    try:
        return update_knowledge_source(
            user=user,
            source_id=source_id,
            payload=payload,
        )

    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "KNOWLEDGE_SOURCE_NOT_FOUND",

                "message":
                    "Knowledge source not found.",
            },
        ) from exc

    except KnowledgeSourceStateError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "INVALID_KNOWLEDGE_STATE",

                "message":
                    str(exc),
            },
        ) from exc

    except psycopg.errors.UniqueViolation as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "KNOWLEDGE_VERSION_EXISTS",

                "message":
                    (
                        "A knowledge source with "
                        "this title and version "
                        "already exists."
                    ),
            },
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_UPDATE_UNAVAILABLE",

                "message":
                    (
                        "The knowledge source "
                        "could not be updated."
                    ),
            },
        ) from exc


@router.post(
    "/sources/{source_id}/publish",
    response_model=
        KnowledgeSourceDetail,
)
def publish_source(
    source_id: UUID,

    user: InternalUser = Depends(
        require_knowledge_manager
    ),
) -> KnowledgeSourceDetail:
    try:
        return publish_knowledge_source(
            user=user,
            source_id=source_id,
        )

    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "KNOWLEDGE_SOURCE_NOT_FOUND",

                "message":
                    "Knowledge source not found.",
            },
        ) from exc

    except KnowledgeSourceStateError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "INVALID_KNOWLEDGE_STATE",

                "message":
                    str(exc),
            },
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_PUBLISH_UNAVAILABLE",

                "message":
                    (
                        "The knowledge source "
                        "could not be published."
                    ),
            },
        ) from exc


@router.post(
    "/sources/{source_id}/retire",
    response_model=
        KnowledgeSourceDetail,
)
def retire_source(
    source_id: UUID,
    payload: KnowledgeRetireRequest,

    user: InternalUser = Depends(
        require_knowledge_manager
    ),
) -> KnowledgeSourceDetail:
    try:
        return retire_knowledge_source(
            user=user,
            source_id=source_id,
            payload=payload,
        )

    except KnowledgeSourceNotFoundError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "KNOWLEDGE_SOURCE_NOT_FOUND",

                "message":
                    "Knowledge source not found.",
            },
        ) from exc

    except KnowledgeSourceStateError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "INVALID_KNOWLEDGE_STATE",

                "message":
                    str(exc),
            },
        ) from exc

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "KNOWLEDGE_RETIRE_UNAVAILABLE",

                "message":
                    (
                        "The knowledge source "
                        "could not be retired."
                    ),
            },
        ) from exc