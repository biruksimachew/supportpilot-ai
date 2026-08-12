from uuid import UUID

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

from app.schemas.evidence_decision import (
    TicketAIDraftResponse,
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
)

from app.services.knowledge_retrieval import (
    KnowledgeRetrievalConsistencyError,
)

from app.services.support_ai import (
    TicketMessageNotFoundError,
    run_ticket_ai_draft,
)


router = APIRouter(
    prefix="/api/v1/agent/tickets",
    tags=["agent-ai"],
)


@router.post(
    (
        "/{ticket_id}"
        "/messages/{message_id}"
        "/ai-draft"
    ),

    response_model=
        TicketAIDraftResponse,
)
def create_ticket_ai_draft(
    ticket_id: UUID,
    message_id: UUID,

    user: InternalUser = Depends(
        get_current_internal_user
    ),

) -> TicketAIDraftResponse:

    try:
        embedding_provider = (
            get_embedding_provider()
        )

        generation_provider = (
            get_generation_provider()
        )


        return run_ticket_ai_draft(
            user=user,

            ticket_id=
                ticket_id,

            message_id=
                message_id,

            embedding_provider=
                embedding_provider,

            generation_provider=
                generation_provider,
        )


    except TicketMessageNotFoundError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "TICKET_MESSAGE_NOT_FOUND",

                "message":
                    str(exc),
            },
        ) from exc


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
                        "AI provider configuration "
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
                    "AI_RUN_UNAVAILABLE",

                "message":
                    (
                        "The AI support run "
                        "could not be completed."
                    ),
            },
        ) from exc