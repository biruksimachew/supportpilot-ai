from uuid import UUID

import psycopg

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Query,
    status,
)

from app.api.routes.knowledge import (
    require_knowledge_manager,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.knowledge_index import (
    KnowledgeIndexResponse,
)

from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    get_embedding_provider,
)

from app.services.knowledge import (
    KnowledgeSourceNotFoundError,
)

from app.services.knowledge_index import (
    KnowledgeIndexConsistencyError,
    KnowledgeIndexStateError,
    index_knowledge_source,
)


router = APIRouter(
    prefix="/api/v1/agent/knowledge",
    tags=["knowledge"],
)


@router.post(
    "/sources/{source_id}/index",
    response_model=
        KnowledgeIndexResponse,
)
def index_source(
    source_id: UUID,

    force: bool = Query(
        default=False,
    ),

    user: InternalUser = Depends(
        require_knowledge_manager
    ),
) -> KnowledgeIndexResponse:
    try:
        provider = (
            get_embedding_provider()
        )

        return index_knowledge_source(
            user=user,
            source_id=source_id,
            provider=provider,
            force=force,
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

    except KnowledgeIndexStateError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "INVALID_KNOWLEDGE_INDEX_STATE",

                "message":
                    str(exc),
            },
        ) from exc

    except EmbeddingConfigurationError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "EMBEDDING_CONFIGURATION_ERROR",

                "message":
                    (
                        "The embedding provider "
                        "is not configured."
                    ),
            },
        ) from exc

    except EmbeddingProviderError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_502_BAD_GATEWAY,

            detail={
                "code":
                    "EMBEDDING_PROVIDER_ERROR",

                "message":
                    (
                        "The embedding provider "
                        "could not complete the request."
                    ),
            },
        ) from exc

    except KnowledgeIndexConsistencyError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "KNOWLEDGE_INDEX_CONSISTENCY_ERROR",

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
                    "KNOWLEDGE_INDEX_UNAVAILABLE",

                "message":
                    (
                        "Knowledge indexing is "
                        "temporarily unavailable."
                    ),
            },
        ) from exc