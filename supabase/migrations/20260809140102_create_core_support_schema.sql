-- SupportPilot AI
-- Core support operations schema
-- Milestone M1D

-- ============================================================
-- Shared trigger function
-- ============================================================

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = timezone('utc', now());
    return new;
end;
$$;


-- ============================================================
-- USERS
-- Application profile attached to Supabase Auth.
-- Authorization/RLS policies are added in M1E.
-- ============================================================

create table public.users (
    id uuid primary key references auth.users(id) on delete cascade,

    role text not null
        check (
            role in (
                'SUPPORT_AGENT',
                'SUPPORT_MANAGER',
                'SYSTEM_ADMIN'
            )
        ),

    name text not null,
    email text not null,

    status text not null default 'ACTIVE'
        check (
            status in (
                'ACTIVE',
                'DISABLED'
            )
        ),

    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create unique index users_email_unique_ci
    on public.users (lower(email));

create index users_role_idx
    on public.users (role);

create trigger users_set_updated_at
before update on public.users
for each row
execute function public.set_updated_at();


-- ============================================================
-- CUSTOMERS
-- Store only support-relevant customer information.
-- ============================================================

create table public.customers (
    id uuid primary key default gen_random_uuid(),

    external_id text unique,
    email text,
    name text,

    verification_metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now())
);

create index customers_email_idx
    on public.customers (lower(email));

create trigger customers_set_updated_at
before update on public.customers
for each row
execute function public.set_updated_at();


-- ============================================================
-- TICKETS
-- Core support case.
-- ============================================================

create table public.tickets (
    id uuid primary key default gen_random_uuid(),

    reference text not null unique
        default (
            'SP-' ||
            upper(
                substr(
                    replace(gen_random_uuid()::text, '-', ''),
                    1,
                    8
                )
            )
        ),

    channel text not null
        check (
            channel in (
                'chat',
                'email'
            )
        ),

    customer_ref uuid references public.customers(id)
        on delete set null,

    status text not null default 'NEW'
        check (
            status in (
                'NEW',
                'TRIAGED',
                'DRAFTED',
                'AUTO_RESPONDED',
                'REVIEW_REQUIRED',
                'WAITING_CUSTOMER',
                'RESOLVED',
                'FAILED'
            )
        ),

    priority text not null default 'P4'
        check (
            priority in (
                'P1',
                'P2',
                'P3',
                'P4'
            )
        ),

    intent text
        check (
            intent is null
            or intent in (
                'order_status',
                'shipping',
                'return',
                'damaged_item',
                'product',
                'account',
                'complaint',
                'other'
            )
        ),

    confidence_band text
        check (
            confidence_band is null
            or confidence_band in (
                'HIGH',
                'MEDIUM',
                'LOW'
            )
        ),

    restricted_action boolean not null default false,

    escalation_reason text,

    assignee_id uuid references public.users(id)
        on delete set null,

    resolution_code text
        check (
            resolution_code is null
            or resolution_code in (
                'AUTO_RESOLVED',
                'AGENT_RESOLVED',
                'CUSTOMER_INFO_REQUIRED',
                'POLICY_EXCEPTION',
                'ORDER_ACTION_REQUIRED',
                'TECHNICAL_FAILURE',
                'DUPLICATE',
                'SPAM'
            )
        ),

    created_at timestamptz not null default timezone('utc', now()),
    updated_at timestamptz not null default timezone('utc', now()),
    resolved_at timestamptz,

    constraint resolved_ticket_requires_resolution_time
        check (
            status <> 'RESOLVED'
            or resolved_at is not null
        )
);

create index tickets_status_idx
    on public.tickets (status);

create index tickets_priority_idx
    on public.tickets (priority);

create index tickets_intent_idx
    on public.tickets (intent);

create index tickets_assignee_idx
    on public.tickets (assignee_id);

create index tickets_customer_idx
    on public.tickets (customer_ref);

create index tickets_created_at_idx
    on public.tickets (created_at desc);

create index tickets_queue_idx
    on public.tickets (
        status,
        priority,
        created_at
    );

create trigger tickets_set_updated_at
before update on public.tickets
for each row
execute function public.set_updated_at();


-- ============================================================
-- MESSAGES
-- Chat and email normalize into this common representation.
-- external_message_id provides channel idempotency protection.
-- ============================================================

create table public.messages (
    id uuid primary key default gen_random_uuid(),

    ticket_id uuid not null
        references public.tickets(id)
        on delete cascade,

    direction text not null
        check (
            direction in (
                'inbound',
                'outbound'
            )
        ),

    sender_type text not null
        check (
            sender_type in (
                'customer',
                'ai',
                'agent',
                'system'
            )
        ),

    body text not null
        check (length(trim(body)) > 0),

    external_message_id text,

    is_internal boolean not null default false,

    sent_at timestamptz not null default timezone('utc', now()),
    created_at timestamptz not null default timezone('utc', now())
);

create unique index messages_external_message_id_unique
    on public.messages (external_message_id)
    where external_message_id is not null;

create index messages_ticket_history_idx
    on public.messages (
        ticket_id,
        sent_at
    );


-- ============================================================
-- ORDER CACHE
-- Read-only commerce facts.
-- No commerce write actions belong in this schema.
-- ============================================================

create table public.orders_cache (
    external_order_id text primary key,

    customer_ref uuid
        references public.customers(id)
        on delete cascade,

    status text not null,

    fulfillment_summary jsonb not null default '{}'::jsonb,
    total_summary jsonb not null default '{}'::jsonb,

    retrieved_at timestamptz not null default timezone('utc', now())
);

create index orders_cache_customer_idx
    on public.orders_cache (customer_ref);

create index orders_cache_retrieved_at_idx
    on public.orders_cache (retrieved_at desc);


-- ============================================================
-- KNOWLEDGE SOURCES
-- Only PUBLISHED content will later be eligible for RAG.
-- ============================================================

create table public.knowledge_sources (
    id uuid primary key default gen_random_uuid(),

    title text not null,

    type text not null
        check (
            type in (
                'POLICY',
                'FAQ',
                'PRODUCT',
                'OPERATIONAL_NOTICE'
            )
        ),

    version text not null,

    status text not null default 'DRAFT'
        check (
            status in (
                'DRAFT',
                'PUBLISHED',
                'RETIRED'
            )
        ),

    effective_at timestamptz,
    last_updated timestamptz not null default timezone('utc', now()),

    checksum text not null,

    created_by uuid references public.users(id)
        on delete set null,

    created_at timestamptz not null default timezone('utc', now()),

    retired_at timestamptz,

    metadata jsonb not null default '{}'::jsonb,

    unique (title, version)
);

create index knowledge_sources_status_idx
    on public.knowledge_sources (status);

create index knowledge_sources_type_idx
    on public.knowledge_sources (type);

create index knowledge_sources_effective_idx
    on public.knowledge_sources (effective_at);

create trigger knowledge_sources_set_updated_at
before update on public.knowledge_sources
for each row
execute function public.set_updated_at();


-- ============================================================
-- KNOWLEDGE CHUNKS
--
-- Deliberately using vector without a fixed dimension.
-- The final dimension must match the selected embedding provider.
-- ============================================================

create table public.knowledge_chunks (
    id uuid primary key default gen_random_uuid(),

    source_id uuid not null
        references public.knowledge_sources(id)
        on delete cascade,

    section text,

    content text not null
        check (length(trim(content)) > 0),

    embedding extensions.vector,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default timezone('utc', now())
);

create index knowledge_chunks_source_idx
    on public.knowledge_chunks (source_id);


-- ============================================================
-- AI RUNS
-- One auditable model execution associated with support work.
-- ============================================================

create table public.ai_runs (
    id uuid primary key default gen_random_uuid(),

    ticket_id uuid not null
        references public.tickets(id)
        on delete cascade,

    message_id uuid
        references public.messages(id)
        on delete set null,

    provider text not null,
    model text not null,
    prompt_version text not null,

    intent text,

    confidence numeric(5,4)
        check (
            confidence is null
            or (
                confidence >= 0
                and confidence <= 1
            )
        ),

    confidence_band text
        check (
            confidence_band is null
            or confidence_band in (
                'HIGH',
                'MEDIUM',
                'LOW'
            )
        ),

    decision text not null
        check (
            decision in (
                'AUTO_RESPOND',
                'REVIEW_REQUIRED',
                'REQUEST_CLARIFICATION',
                'FAILED'
            )
        ),

    decision_reasons jsonb not null default '[]'::jsonb,

    latency_ms integer
        check (
            latency_ms is null
            or latency_ms >= 0
        ),

    error_code text,

    created_at timestamptz not null default timezone('utc', now())
);

create index ai_runs_ticket_idx
    on public.ai_runs (
        ticket_id,
        created_at desc
    );

create index ai_runs_message_idx
    on public.ai_runs (message_id);

create index ai_runs_decision_idx
    on public.ai_runs (decision);


-- ============================================================
-- RETRIEVAL EVIDENCE
-- Exact chunks used by an AI run.
-- ============================================================

create table public.retrieval_evidence (
    ai_run_id uuid not null
        references public.ai_runs(id)
        on delete cascade,

    chunk_id uuid not null
        references public.knowledge_chunks(id)
        on delete restrict,

    rank integer not null
        check (rank > 0),

    score numeric,

    created_at timestamptz not null default timezone('utc', now()),

    primary key (
        ai_run_id,
        chunk_id
    ),

    unique (
        ai_run_id,
        rank
    )
);

create index retrieval_evidence_chunk_idx
    on public.retrieval_evidence (chunk_id);


-- ============================================================
-- TOOL CALLS
-- Narrow application-controlled tools only.
-- ============================================================

create table public.tool_calls (
    id uuid primary key default gen_random_uuid(),

    ai_run_id uuid not null
        references public.ai_runs(id)
        on delete cascade,

    tool_name text not null,

    safe_request_summary text,
    result_summary text,

    status text not null
        check (
            status in (
                'SUCCEEDED',
                'FAILED',
                'BLOCKED'
            )
        ),

    latency_ms integer
        check (
            latency_ms is null
            or latency_ms >= 0
        ),

    created_at timestamptz not null default timezone('utc', now())
);

create index tool_calls_ai_run_idx
    on public.tool_calls (
        ai_run_id,
        created_at
    );


-- ============================================================
-- AGENT ACTIONS
-- Keep AI draft and human edits distinguishable.
-- ============================================================

create table public.agent_actions (
    id uuid primary key default gen_random_uuid(),

    ticket_id uuid not null
        references public.tickets(id)
        on delete cascade,

    user_id uuid
        references public.users(id)
        on delete set null,

    action text not null,

    before_value jsonb,
    after_value jsonb,

    created_at timestamptz not null default timezone('utc', now())
);

create index agent_actions_ticket_idx
    on public.agent_actions (
        ticket_id,
        created_at
    );

create index agent_actions_user_idx
    on public.agent_actions (user_id);


-- ============================================================
-- AUDIT EVENTS
-- Generic immutable operational audit trail.
-- Actor and entity IDs remain text so services/external systems
-- can also participate without artificial FK coupling.
-- ============================================================

create table public.audit_events (
    id uuid primary key default gen_random_uuid(),

    actor_type text not null
        check (
            actor_type in (
                'CUSTOMER',
                'AGENT',
                'MANAGER',
                'ADMIN',
                'AI',
                'SERVICE',
                'SYSTEM'
            )
        ),

    actor_id text,

    event_type text not null,

    entity_type text not null,
    entity_id text not null,

    metadata jsonb not null default '{}'::jsonb,

    created_at timestamptz not null default timezone('utc', now())
);

create index audit_events_entity_idx
    on public.audit_events (
        entity_type,
        entity_id,
        created_at desc
    );

create index audit_events_actor_idx
    on public.audit_events (
        actor_type,
        actor_id,
        created_at desc
    );

create index audit_events_created_at_idx
    on public.audit_events (created_at desc);