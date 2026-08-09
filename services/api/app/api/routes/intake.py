import psycopg
from fastapi import (
    APIRouter,
    HTTPException,
    Response,
    status,
)

from app.schemas.intake import (
    InboundMessageRequest,
    InboundMessageResponse,
)
from app.services.intake import (
    ingest_inbound_message,
)


router = APIRouter(
    prefix="/api/v1/intake",
    tags=["intake"],
)


@router.post(
    "/messages",
    response_model=InboundMessageResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_inbound_message(
    payload: InboundMessageRequest,
    response: Response,
) -> InboundMessageResponse:
    """
    Accept one normalized inbound chat/email message.

    Channel adapters perform transport-specific parsing before
    calling this endpoint.
    """

    try:
        result = ingest_inbound_message(
            payload
        )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "INTAKE_UNAVAILABLE",
                "message": (
                    "Inbound message could not be persisted."
                ),
            },
        ) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK

    return result