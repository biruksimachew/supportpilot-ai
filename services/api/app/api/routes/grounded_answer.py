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

from app.schemas.grounded_generation import (
    GroundedAnswerRequest,
    GroundedAnswerResponse,
)

from app.services.embeddings import (
    EmbeddingConfigurationError,
    EmbeddingProviderError,
    get_embedding_provider,
)

from app.services.generation import (
    GenerationConfigurationError,
    GenerationProviderError,
    get_generation_provider,
)

from app.services.grounded_answer import (
    GroundedGenerationConsistencyError,
    generate_grounded_answer,
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
    "/answer",
    response_model=
        GroundedAnswerResponse,
)
def answer_from_approved_knowledge(
    payload: GroundedAnswerRequest,

    user: InternalUser = Depends(
        get_current_internal_user
    ),
) -> GroundedAnswerResponse:

    _ = user

    try:
        embedding_provider = (
            get_embedding_provider()
        )

        retrieval = (
            retrieve_knowledge(
                question=
                    payload.question,

                provider=
                    embedding_provider,

                top_k=
                    payload.top_k,

                min_similarity=
                    payload.min_similarity,
            )
        )


        if not retrieval.results:
            return generate_grounded_answer(
                question=
                    payload.question,

                retrieval=
                    retrieval,

                provider=
                    get_generation_provider(),
            )


        generation_provider = (
            get_generation_provider()
        )


        return generate_grounded_answer(
            question=
                payload.question,

            retrieval=
                retrieval,

            provider=
                generation_provider,
        )


    except (
        EmbeddingConfigurationError,
        GenerationConfigurationError,
    ) as exc:

        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "AI_CONFIGURATION_ERROR",

                "message":
                    (
                        "The AI provider configuration "
                        "is unavailable."
                    ),
            },
        ) from exc


    except (
        EmbeddingProviderError,
        GenerationProviderError,
    ) as exc:

        raise HTTPException(
            status_code=
                status.HTTP_502_BAD_GATEWAY,

            detail={
                "code":
                    "AI_PROVIDER_ERROR",

                "message":
                    (
                        "An AI provider could not "
                        "complete the request."
                    ),
            },
        ) from exc


    except (
        KnowledgeRetrievalConsistencyError,
        GroundedGenerationConsistencyError,
    ) as exc:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "AI_GROUNDING_ERROR",

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
                    "KNOWLEDGE_UNAVAILABLE",

                "message":
                    (
                        "Approved knowledge is "
                        "temporarily unavailable."
                    ),
            },
        ) from exc