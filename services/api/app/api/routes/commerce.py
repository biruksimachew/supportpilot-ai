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

from app.schemas.commerce import (
    CommerceOrderLookupRequest,
    CommerceOrderLookupResponse,
)

from app.services.commerce import (
    CommerceConfigurationError,
    CommerceProviderError,
    get_commerce_provider,
)

from app.services.commerce_lookup import (
    CommerceAIRunScopeError,
    CommerceCustomerIdentityError,
    CommerceCustomerNotFoundError,
    CommerceIdentityNotVerifiedError,
    CommerceOrderFormatError,
    CommerceOrderNotFoundError,
    lookup_customer_order,
)


router = APIRouter(
    prefix="/api/v1/agent/commerce",
    tags=["commerce"],
)


@router.post(
    "/orders/lookup",
    response_model=CommerceOrderLookupResponse,
)
def lookup_order(
    payload: CommerceOrderLookupRequest,

    user: InternalUser = Depends(
        get_current_internal_user
    ),

) -> CommerceOrderLookupResponse:

    try:

        provider = (
            get_commerce_provider()
        )


        return lookup_customer_order(
            user=user,

            customer_id=
                payload.customer_id,

            order_number=
                payload.order_number,

            ai_run_id=
                payload.ai_run_id,

            provider=
                provider,
        )


    # ------------------------------------------------------
    # Customer record itself does not exist.
    # ------------------------------------------------------

    except CommerceCustomerNotFoundError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "CUSTOMER_NOT_FOUND",

                "message":
                    "Customer not found.",
            },
        ) from exc


    # ------------------------------------------------------
    # The order is unavailable inside this customer's scope.
    #
    # Important:
    # We do not reveal whether the order exists for somebody
    # else.
    # ------------------------------------------------------

    except CommerceOrderNotFoundError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_404_NOT_FOUND,

            detail={
                "code":
                    "ORDER_NOT_FOUND_FOR_CUSTOMER",

                "message":
                    (
                        "Order was not found "
                        "for this customer."
                    ),
            },
        ) from exc


    # ------------------------------------------------------
    # Order number itself is malformed.
    # Example:
    #   abc123
    #
    # Expected Northstar format:
    #   #NS10041
    # ------------------------------------------------------

    except CommerceOrderFormatError as exc:

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


    # ------------------------------------------------------
    # NEW M4B SECURITY HANDLER
    #
    # The AI run attempted commerce access before identity
    # verification was completed for this exact order.
    # ------------------------------------------------------

    except CommerceIdentityNotVerifiedError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "CUSTOMER_NOT_VERIFIED",

                "message":
                    (
                        "Customer identity has "
                        "not been verified for "
                        "this order."
                    ),
            },
        ) from exc


    # ------------------------------------------------------
    # Other customer / AI-run scope problems.
    #
    # Examples:
    # - customer has no commerce external ID
    # - AI run belongs to a different customer
    # ------------------------------------------------------

    except (
        CommerceCustomerIdentityError,
        CommerceAIRunScopeError,
    ) as exc:

        raise HTTPException(
            status_code=
                status.HTTP_409_CONFLICT,

            detail={
                "code":
                    "COMMERCE_SCOPE_ERROR",

                "message":
                    str(exc),
            },
        ) from exc


    # ------------------------------------------------------
    # Commerce integration configuration is invalid.
    # ------------------------------------------------------

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


    # ------------------------------------------------------
    # Commerce provider itself failed.
    # ------------------------------------------------------

    except CommerceProviderError as exc:

        raise HTTPException(
            status_code=
                status.HTTP_502_BAD_GATEWAY,

            detail={
                "code":
                    "COMMERCE_PROVIDER_ERROR",

                "message":
                    (
                        "Commerce lookup "
                        "could not be completed."
                    ),
            },
        ) from exc


    # ------------------------------------------------------
    # Database failure while handling commerce lookup.
    # ------------------------------------------------------

    except psycopg.Error as exc:

        raise HTTPException(
            status_code=
                status.HTTP_503_SERVICE_UNAVAILABLE,

            detail={
                "code":
                    "COMMERCE_LOOKUP_UNAVAILABLE",

                "message":
                    (
                        "Commerce lookup is "
                        "temporarily unavailable."
                    ),
            },
        ) from exc