create table public.outbound_deliveries (
    id uuid primary key
        default gen_random_uuid(),

    ticket_id uuid not null
        references public.tickets(id)
        on delete cascade,

    requested_by uuid
        references public.users(id)
        on delete set null,

    ai_run_id uuid
        references public.ai_runs(id)
        on delete set null,

    draft_action_id uuid
        references public.agent_actions(id)
        on delete set null,

    response_message_id uuid
        references public.messages(id)
        on delete set null,

    idempotency_key uuid not null,

    channel text not null,

    provider text not null,

    destination text,

    subject text,

    body text not null,
    body_checksum text not null,

    status text not null
        default 'PENDING',

    attempt_count integer not null
        default 0,

    provider_message_id text,

    error_code text,
    error_summary text,

    created_at timestamptz not null
        default timezone('utc', now()),

    updated_at timestamptz not null
        default timezone('utc', now()),

    delivered_at timestamptz,

    constraint outbound_deliveries_channel_check
        check (
            channel in (
                'chat',
                'email'
            )
        ),

    constraint outbound_deliveries_status_check
        check (
            status in (
                'PENDING',
                'DELIVERED',
                'FAILED',
                'UNCERTAIN'
            )
        ),

    constraint outbound_deliveries_attempt_count_check
        check (
            attempt_count >= 0
        ),

    constraint outbound_delivery_ticket_key_unique
        unique (
            ticket_id,
            idempotency_key
        )
);


create index outbound_deliveries_ticket_idx
    on public.outbound_deliveries (
        ticket_id,
        created_at desc
    );


create index outbound_deliveries_status_idx
    on public.outbound_deliveries (
        status,
        updated_at
    );


alter table public.outbound_deliveries
    enable row level security;


create policy
    "internal staff can read outbound deliveries"

on public.outbound_deliveries

for select

to authenticated

using (
    (
        select private.current_app_role()
    )
    in (
        'SUPPORT_AGENT',
        'SUPPORT_MANAGER',
        'SYSTEM_ADMIN'
    )
);