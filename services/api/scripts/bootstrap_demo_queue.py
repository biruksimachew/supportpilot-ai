from dataclasses import dataclass
from uuid import UUID

import psycopg

from app.core.config import settings
from app.schemas.intake import (
    InboundMessageRequest,
)
from app.services.intake import (
    ingest_inbound_message,
)


BOOTSTRAP_NAME = "m5-demo-queue"


AMINA_ID = UUID(
    "10000000-0000-4000-8000-000000000001"
)

DANIEL_ID = UUID(
    "10000000-0000-4000-8000-000000000002"
)

MAYA_ID = UUID(
    "10000000-0000-4000-8000-000000000003"
)

NOAH_ID = UUID(
    "10000000-0000-4000-8000-000000000004"
)


@dataclass(frozen=True)
class DemoTicket:
    reference: str

    thread_id: str
    message_id: str

    channel: str
    customer_email: str
    customer_id: UUID

    body: str
    received_at: str

    status: str
    priority: str
    intent: str
    confidence_band: str | None

    restricted_action: bool = False

    escalation_reason: str | None = None

    identity_status: str = "UNVERIFIED"

    identity_method: str | None = None

    verified_order_number: str | None = None

    assign_manager: bool = False


DEMO_TICKETS = (
    DemoTicket(
        reference="SP-DEMO-001",

        thread_id=(
            "demo-m5-refund-review"
        ),

        message_id=(
            "demo-m5-refund-review-001"
        ),

        channel="email",

        customer_email=(
            "daniel.demo@example.com"
        ),

        customer_id=DANIEL_ID,

        body=(
            "Refund #NS10042 now. "
            "I want the money returned "
            "to my card."
        ),

        received_at=(
            "2026-08-13T08:00:00Z"
        ),

        status="REVIEW_REQUIRED",

        priority="P2",

        intent="return",

        confidence_band="HIGH",

        restricted_action=True,

        escalation_reason=(
            "RESTRICTED_ACTION_REFUND"
        ),

        assign_manager=True,
    ),

    DemoTicket(
        reference="SP-DEMO-002",

        thread_id=(
            "demo-m5-damaged-item"
        ),

        message_id=(
            "demo-m5-damaged-item-001"
        ),

        channel="chat",

        customer_email=(
            "maya.demo@example.com"
        ),

        customer_id=MAYA_ID,

        body=(
            "My CampGlow Lantern from "
            "#NS10043 arrived broken. "
            "The housing is cracked."
        ),

        received_at=(
            "2026-08-13T08:05:00Z"
        ),

        status="REVIEW_REQUIRED",

        priority="P2",

        intent="damaged_item",

        confidence_band="HIGH",

        escalation_reason=(
            "DAMAGED_ITEM_REQUIRES_REVIEW"
        ),

        assign_manager=True,
    ),

    DemoTicket(
        reference="SP-DEMO-003",

        thread_id=(
            "demo-m5-order-verification"
        ),

        message_id=(
            "demo-m5-order-verification-001"
        ),

        channel="chat",

        customer_email=(
            "amina.demo@example.com"
        ),

        customer_id=AMINA_ID,

        body=(
            "Where is my order "
            "#NS10041?"
        ),

        received_at=(
            "2026-08-13T08:10:00Z"
        ),

        status="WAITING_CUSTOMER",

        priority="P3",

        intent="order_status",

        confidence_band="HIGH",

        escalation_reason=(
            "IDENTITY_VERIFICATION_REQUIRED"
        ),
    ),

    DemoTicket(
        reference="SP-DEMO-004",

        thread_id=(
            "demo-m5-verified-order"
        ),

        message_id=(
            "demo-m5-verified-order-001"
        ),

        channel="chat",

        customer_email=(
            "amina.demo@example.com"
        ),

        customer_id=AMINA_ID,

        body=(
            "Can you tell me the latest "
            "status of order #NS10041?"
        ),

        received_at=(
            "2026-08-13T08:15:00Z"
        ),

        status="DRAFTED",

        priority="P3",

        intent="order_status",

        confidence_band="HIGH",

        identity_status="VERIFIED",

        identity_method=(
            "EMAIL_POSTCODE_ORDER"
        ),

        verified_order_number=(
            "#NS10041"
        ),
    ),

    DemoTicket(
        reference="SP-DEMO-005",

        thread_id=(
            "demo-m5-return-policy"
        ),

        message_id=(
            "demo-m5-return-policy-001"
        ),

        channel="email",

        customer_email=(
            "daniel.demo@example.com"
        ),

        customer_id=DANIEL_ID,

        body=(
            "I received my Summit Flask "
            "18 days ago and have not used "
            "it. Can I return it?"
        ),

        received_at=(
            "2026-08-13T08:20:00Z"
        ),

        status="DRAFTED",

        priority="P3",

        intent="return",

        confidence_band="HIGH",
    ),

    DemoTicket(
        reference="SP-DEMO-006",

        thread_id=(
            "demo-m5-product-question"
        ),

        message_id=(
            "demo-m5-product-question-001"
        ),

        channel="chat",

        customer_email=(
            "amina.demo@example.com"
        ),

        customer_id=AMINA_ID,

        body=(
            "Is the TrailPack 28L "
            "waterproof?"
        ),

        received_at=(
            "2026-08-13T08:25:00Z"
        ),

        status="DRAFTED",

        priority="P4",

        intent="product",

        confidence_band="HIGH",
    ),
)


def find_demo_assignee() -> UUID | None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select id
                from public.users
                where
                    status = 'ACTIVE'
                    and role in (
                        'SUPPORT_MANAGER',
                        'SYSTEM_ADMIN',
                        'SUPPORT_AGENT'
                    )
                order by
                    case role
                        when 'SUPPORT_MANAGER'
                            then 1
                        when 'SYSTEM_ADMIN'
                            then 2
                        when 'SUPPORT_AGENT'
                            then 3
                        else 4
                    end,
                    created_at
                limit 1;
                """
            )

            row = cursor.fetchone()

    if row is None:
        return None

    return row[0]


def ensure_customer_exists(
    customer_id: UUID,
) -> None:
    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select 1
                from public.customers
                where id = %s;
                """,
                (customer_id,),
            )

            exists = (
                cursor.fetchone()
                is not None
            )

    if not exists:
        raise RuntimeError(
            (
                "Required synthetic customer "
                f"{customer_id} is missing. "
                "Run `npx supabase db reset` "
                "before bootstrapping the "
                "demo queue."
            )
        )


def create_or_find_ticket(
    demo: DemoTicket,
) -> UUID:
    result = ingest_inbound_message(
        InboundMessageRequest(
            channel=demo.channel,

            external_message_id=(
                demo.message_id
            ),

            external_thread_id=(
                demo.thread_id
            ),

            customer_hint=(
                demo.customer_email
            ),

            body=demo.body,

            received_at=(
                demo.received_at
            ),

            attachments=[],

            metadata={
                "demo": True,
                "bootstrap": (
                    BOOTSTRAP_NAME
                ),
                "reference": (
                    demo.reference
                ),
            },
        )
    )

    return result.ticket_id


def apply_demo_state(
    *,
    demo: DemoTicket,
    ticket_id: UUID,
    assignee_id: UUID | None,
) -> None:
    assigned_user = (
        assignee_id
        if demo.assign_manager
        else None
    )

    identity_verified_at = (
        "timezone('utc', now())"
        if (
            demo.identity_status
            == "VERIFIED"
        )
        else "null"
    )

    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                f"""
                update public.tickets
                set
                    reference = %s,
                    customer_ref = %s,

                    status = %s,
                    priority = %s,
                    intent = %s,

                    confidence_band = %s,

                    restricted_action = %s,

                    escalation_reason = %s,

                    assignee_id = %s,

                    resolution_code = null,
                    resolved_at = null,

                    identity_verification_status
                        = %s,

                    identity_verification_method
                        = %s,

                    identity_verified_at
                        = {identity_verified_at},

                    identity_verified_order_number
                        = %s,

                    identity_verification_attempts
                        = case
                            when %s = 'VERIFIED'
                                then 1
                            else 0
                          end

                where id = %s;
                """,
                (
                    demo.reference,

                    demo.customer_id,

                    demo.status,
                    demo.priority,
                    demo.intent,

                    demo.confidence_band,

                    demo.restricted_action,

                    demo.escalation_reason,

                    assigned_user,

                    demo.identity_status,

                    demo.identity_method,

                    demo.verified_order_number,

                    demo.identity_status,

                    ticket_id,
                ),
            )

            if cursor.rowcount != 1:
                raise RuntimeError(
                    (
                        "Could not update "
                        f"{demo.reference}."
                    )
                )


def verify_demo_queue() -> None:
    expected_references = [
        demo.reference
        for demo in DEMO_TICKETS
    ]

    with psycopg.connect(
        settings.database_url
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select
                    reference,
                    status,
                    priority,
                    intent,
                    restricted_action,
                    identity_verification_status
                from public.tickets
                where reference = any(%s)
                order by reference;
                """,
                (
                    expected_references,
                ),
            )

            rows = cursor.fetchall()

    if len(rows) != len(
        DEMO_TICKETS
    ):
        raise RuntimeError(
            (
                "Demo queue verification "
                "failed: expected "
                f"{len(DEMO_TICKETS)} "
                "tickets but found "
                f"{len(rows)}."
            )
        )

    print("")
    print(
        "Demo support queue"
    )
    print(
        "------------------"
    )

    for row in rows:
        (
            reference,
            status,
            priority,
            intent,
            restricted_action,
            identity_status,
        ) = row

        restriction = (
            "restricted"
            if restricted_action
            else "safe"
        )

        print(
            (
                f"{reference}: "
                f"{priority} "
                f"{status} "
                f"{intent} "
                f"{identity_status} "
                f"{restriction}"
            )
        )


def main() -> None:
    print(
        (
            "Bootstrapping deterministic "
            "M5 demo support queue..."
        )
    )

    for demo in DEMO_TICKETS:
        ensure_customer_exists(
            demo.customer_id
        )

    assignee_id = (
        find_demo_assignee()
    )

    if assignee_id is None:
        print(
            (
                "No active staff member "
                "found. Review tickets "
                "will remain unassigned."
            )
        )
    else:
        print(
            (
                "Active demo assignee: "
                f"{assignee_id}"
            )
        )

    for demo in DEMO_TICKETS:
        ticket_id = (
            create_or_find_ticket(
                demo
            )
        )

        apply_demo_state(
            demo=demo,
            ticket_id=ticket_id,
            assignee_id=assignee_id,
        )

        print(
            (
                f"Prepared "
                f"{demo.reference}"
            )
        )

    verify_demo_queue()

    print("")
    print(
        (
            "M5 demo support queue "
            "bootstrap complete."
        )
    )


if __name__ == "__main__":
    main()