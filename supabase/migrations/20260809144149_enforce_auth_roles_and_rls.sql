-- SupportPilot AI
-- Authentication / RBAC / RLS baseline
-- Milestone M1E

-- ============================================================
-- PRIVATE SECURITY HELPERS
-- ============================================================

create schema if not exists private;

revoke all on schema private from public;
revoke all on schema private from anon;

grant usage on schema private to authenticated;


create or replace function private.current_app_role()
returns text
language sql
stable
security definer
set search_path = ''
as $$
    select u.role
    from public.users as u
    where u.id = (select auth.uid())
      and u.status = 'ACTIVE'
    limit 1;
$$;

revoke all
on function private.current_app_role()
from public, anon;

grant execute
on function private.current_app_role()
to authenticated;


-- ============================================================
-- REMOVE DEFAULT DIRECT CLIENT ACCESS
-- ============================================================

revoke all on table public.users from anon, authenticated;
revoke all on table public.customers from anon, authenticated;
revoke all on table public.tickets from anon, authenticated;
revoke all on table public.messages from anon, authenticated;
revoke all on table public.orders_cache from anon, authenticated;
revoke all on table public.knowledge_sources from anon, authenticated;
revoke all on table public.knowledge_chunks from anon, authenticated;
revoke all on table public.ai_runs from anon, authenticated;
revoke all on table public.retrieval_evidence from anon, authenticated;
revoke all on table public.tool_calls from anon, authenticated;
revoke all on table public.agent_actions from anon, authenticated;
revoke all on table public.audit_events from anon, authenticated;


-- Authenticated users get READ access only.
-- RLS determines which rows are visible.
-- Mutations will go through the SupportPilot API.

grant select on table public.users to authenticated;
grant select on table public.customers to authenticated;
grant select on table public.tickets to authenticated;
grant select on table public.messages to authenticated;
grant select on table public.orders_cache to authenticated;
grant select on table public.knowledge_sources to authenticated;
grant select on table public.knowledge_chunks to authenticated;
grant select on table public.ai_runs to authenticated;
grant select on table public.retrieval_evidence to authenticated;
grant select on table public.tool_calls to authenticated;
grant select on table public.agent_actions to authenticated;
grant select on table public.audit_events to authenticated;


-- ============================================================
-- ENABLE RLS
-- ============================================================

alter table public.users enable row level security;
alter table public.customers enable row level security;
alter table public.tickets enable row level security;
alter table public.messages enable row level security;
alter table public.orders_cache enable row level security;
alter table public.knowledge_sources enable row level security;
alter table public.knowledge_chunks enable row level security;
alter table public.ai_runs enable row level security;
alter table public.retrieval_evidence enable row level security;
alter table public.tool_calls enable row level security;
alter table public.agent_actions enable row level security;
alter table public.audit_events enable row level security;


-- ============================================================
-- USER DIRECTORY
--
-- Agents can see active staff for assignment/display.
-- Managers/admins can also inspect disabled accounts.
-- Disabled users themselves receive no application access because
-- private.current_app_role() only returns ACTIVE profiles.
-- ============================================================

create policy "internal staff can read permitted user directory"
on public.users
for select
to authenticated
using (
    (
        (select private.current_app_role())
        in ('SUPPORT_MANAGER', 'SYSTEM_ADMIN')
    )
    or
    (
        (select private.current_app_role()) = 'SUPPORT_AGENT'
        and status = 'ACTIVE'
    )
);


-- ============================================================
-- CUSTOMER / SUPPORT OPERATIONS
-- ============================================================

create policy "internal staff can read customers"
on public.customers
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read tickets"
on public.tickets
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read messages"
on public.messages
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read order cache"
on public.orders_cache
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


-- ============================================================
-- KNOWLEDGE BASE
--
-- Agents only see published evidence.
-- Managers/admins can inspect draft, published and retired
-- versions because they own knowledge operations.
-- ============================================================

create policy "staff can read permitted knowledge sources"
on public.knowledge_sources
for select
to authenticated
using (
    (
        (select private.current_app_role())
        in ('SUPPORT_MANAGER', 'SYSTEM_ADMIN')
    )
    or
    (
        (select private.current_app_role()) = 'SUPPORT_AGENT'
        and status = 'PUBLISHED'
    )
);


create policy "staff can read permitted knowledge chunks"
on public.knowledge_chunks
for select
to authenticated
using (
    (
        (select private.current_app_role())
        in ('SUPPORT_MANAGER', 'SYSTEM_ADMIN')
    )
    or
    (
        (select private.current_app_role()) = 'SUPPORT_AGENT'
        and exists (
            select 1
            from public.knowledge_sources as source
            where source.id = knowledge_chunks.source_id
              and source.status = 'PUBLISHED'
        )
    )
);


-- ============================================================
-- AI / RETRIEVAL / TOOL TRACE
-- ============================================================

create policy "internal staff can read ai runs"
on public.ai_runs
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read retrieval evidence"
on public.retrieval_evidence
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read tool calls"
on public.tool_calls
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


-- ============================================================
-- HUMAN ACTION / AUDIT HISTORY
-- ============================================================

create policy "internal staff can read agent actions"
on public.agent_actions
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);


create policy "internal staff can read audit events"
on public.audit_events
for select
to authenticated
using (
    (select private.current_app_role())
    in ('SUPPORT_AGENT', 'SUPPORT_MANAGER', 'SYSTEM_ADMIN')
);