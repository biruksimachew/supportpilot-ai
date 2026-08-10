from app.schemas.email_intake import (
    EmailInboundRequest,
    EmailInboundResponse,
)

from app.schemas.intake import (
    InboundMessageRequest,
)

from app.services.intake import (
    ingest_inbound_message,
)


def ingest_email_message(
    payload: EmailInboundRequest,
) -> EmailInboundResponse:
    normalized_provider = payload.provider.strip().lower()

    external_message_id = (
        f"{normalized_provider}:"
        f"{payload.external_message_id}"
    )

    external_thread_id = (
        f"{normalized_provider}:"
        f"{payload.external_thread_id}"
    )

    metadata = {
        **payload.metadata,
        "adapter": "email",
        "provider": normalized_provider,
        "provider_message_id":
            payload.external_message_id,
        "provider_thread_id":
            payload.external_thread_id,
    }

    if payload.from_name:
        metadata["from_name"] = payload.from_name

    intake_payload = InboundMessageRequest(
            channel="email",
            external_message_id=
                external_message_id,
            external_thread_id=
                external_thread_id,
            customer_hint=
                str(payload.from_email),
            subject=
                payload.subject,
            body=
                payload.body,
            received_at=
                payload.received_at,
            attachments=
                payload.attachments,
            metadata=
                metadata,
        )

    result = ingest_inbound_message(
            intake_payload,
        )

    return EmailInboundResponse(
        ticket_id=
            str(result.ticket_id),
        ticket_reference=
            result.ticket_reference,
        ticket_status=
            result.ticket_status,
        message_id=
            str(result.message_id),
        duplicate=
            result.duplicate,
        created_ticket=
            result.created_ticket,
    )