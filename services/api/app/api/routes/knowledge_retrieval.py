import psycopg

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    status,
)

from app.core.auth import (
    get_current_internal_user,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.knowledge_retrieval import (
    KnowledgeRetrievalRequest,
    KnowledgeRetrievalResponse,
)

from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    get_embedding_provider,
)

from app.services.knowledge_retrieval import (
    KnowledgeRetrievalConsistencyError,
    retrieve_knowledge,
)


router = APIRouter(
    prefix="/api/v1/agent/knowledge",
    tags=["knowledge"],
)


@router.post(
    "/retrieve",
    response_model=
        KnowledgeRetrievalResponse,
)
def retrieve_approved_knowledge(
    payload: KnowledgeRetrievalRequest,

    user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> KnowledgeRetrievalResponse:
    # Dependency intentionally establishes that
    # the caller is active internal staff.
    _ = user

    try:
        provider = (
            get_embedding_provider()
        )

        return retrieve_knowledge(
            question=
                payload.question,

            provider=
                provider,

            top_k=
                payload.top_k,

            min_similarity=
                payload.min_similarity,
        )

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
                        "could not process the query."
                    ),
            },
        ) from exc

    except KnowledgeRetrievalConsistencyError as exc:
        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "KNOWLEDGE_RETRIEVAL_CONSISTENCY_ERROR",

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
                    "KNOWLEDGE_RETRIEVAL_UNAVAILABLE",

                "message":
                    (
                        "Knowledge retrieval is "
                        "temporarily unavailable."
                    ),
            },
        ) from exc