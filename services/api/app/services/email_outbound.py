import json
import socket

from dataclasses import dataclass

from urllib.error import (
    HTTPError,
    URLError,
)

from urllib.request import (
    Request,
    urlopen,
)

from uuid import UUID

from app.core.config import (
    settings,
)


class EmailOutboundConfigurationError(
    RuntimeError
):
    pass


class EmailOutboundConfirmedFailure(
    RuntimeError
):
    pass


class EmailOutboundUncertainError(
    RuntimeError
):
    pass


@dataclass(frozen=True)
class EmailOutboundResult:
    provider_message_id: str

    provider_thread_id: str | None


def validate_email_outbound_configuration() -> None:

    if (
        len(
            settings.email_outbound_secret
        )
        < 32
    ):
        raise EmailOutboundConfigurationError(
            (
                "Email outbound secret "
                "is not configured."
            )
        )

    if not (
        settings
        .n8n_email_outbound_url
        .strip()
    ):
        raise EmailOutboundConfigurationError(
            (
                "Email outbound URL "
                "is not configured."
            )
        )


def _parse_json_body(
    raw: bytes,
) -> dict:

    if not raw:
        return {}

    try:
        value = json.loads(
            raw.decode(
                "utf-8"
            )
        )

    except (
        UnicodeDecodeError,
        json.JSONDecodeError,
    ):
        return {}

    if not isinstance(
        value,
        dict,
    ):
        return {}

    return value


def deliver_email_via_n8n(
    *,
    delivery_id: UUID,

    idempotency_key: UUID,

    thread_id: str,

    message_id: str,

    destination: str,

    subject: str | None,

    body: str,
) -> EmailOutboundResult:

    validate_email_outbound_configuration()


    payload = {
        "delivery_id":
            str(
                delivery_id
            ),

        "idempotency_key":
            str(
                idempotency_key
            ),

        "thread_id":
            thread_id,

        "message_id":
            message_id,

        "destination":
            destination,

        "subject":
            subject,

        "body":
            body,
    }


    request = Request(
        url=
            settings
            .n8n_email_outbound_url,

        method=
            "POST",

        data=
            json.dumps(
                payload
            ).encode(
                "utf-8"
            ),

        headers={
            "Content-Type":
                "application/json",

            "Accept":
                "application/json",

            (
                "X-SupportPilot-"
                "Outbound-Secret"
            ):
                settings
                .email_outbound_secret,
        },
    )


    try:

        with urlopen(
            request,

            timeout=
                settings
                .email_outbound_timeout_seconds,

        ) as response:

            response_body = (
                _parse_json_body(
                    response.read()
                )
            )


    except HTTPError as exc:

        error_body = (
            _parse_json_body(
                exc.read()
            )
        )


        # Only an explicit response from the
        # workflow proving Gmail rejected the
        # operation is considered a confirmed
        # failure.
        if (
            error_body.get(
                "status"
            )
            == "FAILED"

            and error_body.get(
                "confirmed_failure"
            )
            is True
        ):

            raise EmailOutboundConfirmedFailure(
                str(
                    error_body.get(
                        "error_code"
                    )
                    or
                    "GMAIL_REPLY_FAILED"
                )
            ) from exc


        # A generic HTTP failure may occur after
        # Gmail accepted the message but before
        # the response reached SupportPilot.
        raise EmailOutboundUncertainError(
            (
                "Email delivery outcome "
                "could not be confirmed."
            )
        ) from exc


    except (
        URLError,
        TimeoutError,
        socket.timeout,
        ConnectionError,
    ) as exc:

        raise EmailOutboundUncertainError(
            (
                "Email delivery outcome "
                "could not be confirmed."
            )
        ) from exc


    status = (
        response_body.get(
            "status"
        )
    )


    if status == "FAILED":

        if (
            response_body.get(
                "confirmed_failure"
            )
            is True
        ):
            raise EmailOutboundConfirmedFailure(
                str(
                    response_body.get(
                        "error_code"
                    )
                    or
                    "GMAIL_REPLY_FAILED"
                )
            )

        raise EmailOutboundUncertainError(
            (
                "Email workflow returned "
                "an ambiguous failure."
            )
        )


    if status != "DELIVERED":

        raise EmailOutboundUncertainError(
            (
                "Email workflow response "
                "could not prove delivery."
            )
        )


    provider_message_id = str(
        response_body.get(
            "provider_message_id"
        )
        or ""
    ).strip()


    if not provider_message_id:

        # A 2xx response without the Gmail message
        # ID is still unsafe to retry automatically:
        # Gmail may already have accepted it.
        raise EmailOutboundUncertainError(
            (
                "Email delivery returned "
                "without a provider message ID."
            )
        )


    provider_thread_id_raw = (
        response_body.get(
            "provider_thread_id"
        )
    )


    provider_thread_id = (
        str(
            provider_thread_id_raw
        )

        if provider_thread_id_raw
        is not None

        else None
    )


    return EmailOutboundResult(
        provider_message_id=
            provider_message_id,

        provider_thread_id=
            provider_thread_id,
    )