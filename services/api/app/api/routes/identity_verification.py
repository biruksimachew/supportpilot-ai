import psycopg

from uuid import UUID

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

from app.schemas.identity_verification import (
    CustomerVerificationRequest,
    CustomerVerificationResponse,
)

from app.services.commerce import (
    CommerceConfigurationError,
    CommerceProviderError,
    get_commerce_provider,
)

from app.services.identity_verification import (
    VerificationOrderFormatError,
    VerificationTicketNotFoundError,
    verify_ticket_customer,
)


router = APIRouter(
    prefix="/api/v1/agent/tickets",
    tags=["customer-verification"],
)


@router.post(
    "/{ticket_id}/identity/verify",

    response_model=
        CustomerVerificationResponse,
)
def verify_customer_identity(
    ticket_id: UUID,

    payload:
        CustomerVerificationRequest,

    user: InternalUser = Depends(
        get_current_internal_user
    ),

) -> CustomerVerificationResponse:

    try:

        provider = (
            get_commerce_provider()
        )


        return verify_ticket_customer(
            user=
                user,

            ticket_id=
                ticket_id,

            email=
                str(
                    payload.email
                ),

            postcode=
                payload.postcode,

            order_number=
                payload.order_number,

            provider=
                provider,
        )


    except VerificationTicketNotFoundError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "TICKET_NOT_FOUND",

                "message":
                    "Ticket not found.",
            },
        ) from exc


    except VerificationOrderFormatError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_422_UNPROCESSABLE_CONTENT,

            detail={
                "code":
                    "INVALID_ORDER_NUMBER",

                "message":
                    str(exc),
            },
        ) from exc


    except CommerceConfigurationError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "COMMERCE_CONFIGURATION_ERROR",

                "message":
                    (
                        "Commerce integration "
                        "is not configured."
                    ),
            },
        ) from exc


    except CommerceProviderError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_502_BAD_GATEWAY,

            detail={
                "code":
                    "COMMERCE_PROVIDER_ERROR",

                "message":
                    (
                        "Identity verification "
                        "could not be completed."
                    ),
            },
        ) from exc


    except psycopg.Error as exc:

        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "VERIFICATION_UNAVAILABLE",

                "message":
                    (
                        "Identity verification "
                        "is temporarily unavailable."
                    ),
            },
        ) from exc