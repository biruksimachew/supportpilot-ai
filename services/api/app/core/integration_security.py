import hmac

from fastapi import (
    Header,
    HTTPException,
    status,
)

from app.core.config import settings


def require_email_ingest_secret(
    x_supportpilot_ingest_secret: str | None = Header(
        default=None,
        alias="X-SupportPilot-Ingest-Secret",
    ),
) -> None:
    expected = settings.email_ingest_secret

    if len(expected) < 32:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "EMAIL_INGEST_CONFIGURATION_ERROR",
                "message": (
                    "Email ingestion is temporarily unavailable."
                ),
            },
        )

    if (
        not x_supportpilot_ingest_secret
        or not hmac.compare_digest(
            x_supportpilot_ingest_secret,
            expected,
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "code": "INVALID_INGEST_CREDENTIAL",
                "message": (
                    "A valid integration credential is required."
                ),
            },
        )