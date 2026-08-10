import psycopg

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    Response,
    status,
)

from app.core.integration_security import (
    require_email_ingest_secret,
)

from app.schemas.email_intake import (
    EmailInboundRequest,
    EmailInboundResponse,
)

from app.services.email_intake import (
    ingest_email_message,
)


router = APIRouter(
    prefix="/api/v1/integrations/email",
    tags=["integrations"],
)


@router.post(
    "/messages",
    response_model=EmailInboundResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_email_message(
    payload: EmailInboundRequest,
    response: Response,
    _authorized: None = Depends(
        require_email_ingest_secret
    ),
) -> EmailInboundResponse:
    try:
        result = ingest_email_message(
                payload
            )

    except psycopg.Error as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EMAIL_INGEST_UNAVAILABLE",
                "message": (
                    "The email message could not be persisted."
                ),
            },
        ) from exc

    if result.duplicate:
        response.status_code = status.HTTP_200_OK

    return result