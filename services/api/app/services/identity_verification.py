import hmac
import re

from uuid import UUID

from psycopg.rows import dict_row
from psycopg.types.json import Jsonb

from app.core.database import (
    get_database_connection,
)

from app.schemas.auth import (
    InternalUser,
)

from app.schemas.identity_verification import (
    CustomerVerificationResponse,
)

from app.services.commerce import (
    CommerceProvider,
)


ORDER_NUMBER_PATTERN = re.compile(
    r"^#NS[0-9]{5}$"
)


VERIFICATION_METHOD = (
    "EMAIL_POSTCODE_ORDER"
)


class VerificationTicketNotFoundError(
    LookupError
):
    pass


class VerificationOrderFormatError(
    ValueError
):
    pass


def _actor_type(
    user: InternalUser,
) -> str:

    mapping = {
        "SUPPORT_AGENT":
            "AGENT",

        "SUPPORT_MANAGER":
            "MANAGER",

        "SYSTEM_ADMIN":
            "ADMIN",
    }

    return mapping[
        user.role
    ]


def _normalize_email(
    value: str,
) -> str:

    return (
        value
        .strip()
        .casefold()
    )


def _normalize_postcode(
    value: str,
) -> str:

    return "".join(
        character
        for character
        in value.strip().upper()
        if character.isalnum()
    )


def normalize_order_number(
    value: str,
) -> str:

    normalized = (
        value
        .strip()
        .upper()
    )


    if (
        normalized
        and not normalized.startswith(
            "#"
        )
    ):
        normalized = (
            "#"
            + normalized
        )


    if not ORDER_NUMBER_PATTERN.fullmatch(
        normalized
    ):
        raise VerificationOrderFormatError(
            (
                "Order number must match "
                "the Northstar format "
                "#NS10041."
            )
        )


    return normalized


def _load_ticket(
    *,
    ticket_id: UUID,
) -> dict:

    with get_database_connection() as connection:

        connection.row_factory = dict_row

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    id,
                    customer_ref,

                    identity_verification_status,
                    identity_verification_method,
                    identity_verified_at,
                    identity_verified_order_number,
                    identity_verification_attempts

                from public.tickets

                where id = %s

                limit 1;
                """,
                (
                    ticket_id,
                ),
            )


            row = cursor.fetchone()


    if row is None:

        raise VerificationTicketNotFoundError(
            "Ticket not found."
        )


    return row


def _find_customer_by_email(
    *,
    email: str,
) -> dict | None:

    with get_database_connection() as connection:

        connection.row_factory = dict_row

        with connection.cursor() as cursor:

            cursor.execute(
                """
                select
                    id,
                    external_id,
                    email,
                    verification_metadata

                from public.customers

                where lower(email) = %s

                limit 1;
                """,
                (
                    email,
                ),
            )


            return cursor.fetchone()


def _postcode_matches(
    *,
    customer: dict,
    supplied_postcode: str,
) -> bool:

    metadata = (
        customer[
            "verification_metadata"
        ]
        or {}
    )


    expected = (
        metadata.get(
            "postcode_hint"
        )
    )


    if expected is None:
        return False


    normalized_expected = (
        _normalize_postcode(
            str(
                expected
            )
        )
    )


    normalized_supplied = (
        _normalize_postcode(
            supplied_postcode
        )
    )


    if (
        not normalized_expected
        or not normalized_supplied
    ):
        return False


    return hmac.compare_digest(
        normalized_expected,
        normalized_supplied,
    )


def _record_verification(
    *,
    user: InternalUser,

    ticket_id: UUID,

    verified: bool,

    customer_id:
        UUID | None,

    order_number: str,

    attempts: int,
) -> CustomerVerificationResponse:

    with get_database_connection() as connection:

        connection.row_factory = dict_row


        with connection.transaction():

            with connection.cursor() as cursor:

                if verified:

                    cursor.execute(
                        """
                        update public.tickets

                        set
                            customer_ref = %s,

                            identity_verification_status =
                                'VERIFIED',

                            identity_verification_method =
                                %s,

                            identity_verified_at =
                                now(),

                            identity_verified_order_number =
                                %s,

                            identity_verification_attempts =
                                %s

                        where id = %s

                        returning
                            customer_ref,
                            identity_verification_status,
                            identity_verification_method,
                            identity_verified_at,
                            identity_verified_order_number,
                            identity_verification_attempts;
                        """,
                        (
                            customer_id,

                            VERIFICATION_METHOD,

                            order_number,

                            attempts,

                            ticket_id,
                        ),
                    )

                else:

                    cursor.execute(
                        """
                        update public.tickets

                        set
                            identity_verification_status =
                                'FAILED',

                            identity_verification_method =
                                null,

                            identity_verified_at =
                                null,

                            identity_verified_order_number =
                                null,

                            identity_verification_attempts =
                                %s

                        where id = %s

                        returning
                            customer_ref,
                            identity_verification_status,
                            identity_verification_method,
                            identity_verified_at,
                            identity_verified_order_number,
                            identity_verification_attempts;
                        """,
                        (
                            attempts,
                            ticket_id,
                        ),
                    )


                ticket = cursor.fetchone()


                cursor.execute(
                    """
                    insert into public.audit_events (
                        actor_type,
                        actor_id,

                        event_type,

                        entity_type,
                        entity_id,

                        metadata
                    )

                    values (
                        %s,
                        %s,

                        'CUSTOMER_IDENTITY_VERIFICATION',

                        'ticket',
                        %s,

                        %s
                    );
                    """,
                    (
                        _actor_type(
                            user
                        ),

                        str(
                            user.id
                        ),

                        str(
                            ticket_id
                        ),

                        Jsonb(
                            {
                                "ticket_id":
                                    str(
                                        ticket_id
                                    ),

                                "outcome":
                                    (
                                        "VERIFIED"
                                        if verified
                                        else "FAILED"
                                    ),

                                "method":
                                    VERIFICATION_METHOD,

                                "order_number":
                                    order_number,

                                "attempt":
                                    attempts,
                            }
                        ),
                    )
                )


    if not verified:

        return CustomerVerificationResponse(
            ticket_id=
                ticket_id,

            verification_status=
                "FAILED",

            verified=
                False,

            customer_id=
                None,

            verified_order_number=
                None,

            verification_method=
                None,

            attempts=
                attempts,

            verified_at=
                None,
        )


    return CustomerVerificationResponse(
        ticket_id=
            ticket_id,

        verification_status=
            "VERIFIED",

        verified=
            True,

        customer_id=
            ticket[
                "customer_ref"
            ],

        verified_order_number=
            ticket[
                "identity_verified_order_number"
            ],

        verification_method=
            ticket[
                "identity_verification_method"
            ],

        attempts=
            ticket[
                "identity_verification_attempts"
            ],

        verified_at=
            ticket[
                "identity_verified_at"
            ],
    )


def verify_ticket_customer(
    *,
    user: InternalUser,

    ticket_id: UUID,

    email: str,
    postcode: str,
    order_number: str,

    provider: CommerceProvider,

) -> CustomerVerificationResponse:

    normalized_order_number = (
        normalize_order_number(
            order_number
        )
    )


    ticket = _load_ticket(
        ticket_id=
            ticket_id
    )


    # Already-verified tickets remain stable.
    #
    # Verification is scoped to the exact order number that
    # was proven at verification time.
    if (
        ticket[
            "identity_verification_status"
        ]
        == "VERIFIED"
    ):

        if (
            ticket[
                "identity_verified_order_number"
            ]
            ==
            normalized_order_number
        ):

            return CustomerVerificationResponse(
                ticket_id=
                    ticket_id,

                verification_status=
                    "VERIFIED",

                verified=
                    True,

                customer_id=
                    ticket[
                        "customer_ref"
                    ],

                verified_order_number=
                    ticket[
                        "identity_verified_order_number"
                    ],

                verification_method=
                    ticket[
                        "identity_verification_method"
                    ],

                attempts=
                    ticket[
                        "identity_verification_attempts"
                    ],

                verified_at=
                    ticket[
                        "identity_verified_at"
                    ],
            )


        # Do not destroy a previously valid verification just
        # because someone attempts another order number.
        return CustomerVerificationResponse(
            ticket_id=
                ticket_id,

            verification_status=
                "FAILED",

            verified=
                False,

            customer_id=
                None,

            verified_order_number=
                None,

            verification_method=
                None,

            attempts=
                ticket[
                    "identity_verification_attempts"
                ],
        )


    attempts = (
        ticket[
            "identity_verification_attempts"
        ]
        + 1
    )


    normalized_email = (
        _normalize_email(
            email
        )
    )


    customer = (
        _find_customer_by_email(
            email=
                normalized_email
        )
    )


    verified = False

    verified_customer_id = None


    if (
        customer is not None
        and _postcode_matches(
            customer=
                customer,

            supplied_postcode=
                postcode,
        )
    ):

        order = provider.lookup_order(
            customer_external_id=
                customer[
                    "external_id"
                ],

            order_number=
                normalized_order_number,
        )


        if order is not None:

            verified = True

            verified_customer_id = (
                customer[
                    "id"
                ]
            )


    return _record_verification(
        user=
            user,

        ticket_id=
            ticket_id,

        verified=
            verified,

        customer_id=
            verified_customer_id,

        order_number=
            normalized_order_number,

        attempts=
            attempts,
    )