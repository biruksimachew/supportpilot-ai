-- ============================================================
-- SupportPilot AI
-- Milestone M2A
-- Common inbound channel / ticketing contract
-- ============================================================


-- ============================================================
-- TICKETS
--
-- external_thread_id represents:
--   chat  -> browser/support session identifier
--   email -> provider thread identifier
--
-- Only one non-resolved ticket may own the same channel thread.
-- ============================================================

alter table public.tickets
add column external_thread_id text;


create index tickets_channel_thread_idx
on public.tickets (
    channel,
    external_thread_id
)
where external_thread_id is not null;


create unique index tickets_active_channel_thread_unique
on public.tickets (
    channel,
    external_thread_id
)
where external_thread_id is not null
  and status <> 'RESOLVED';


-- ============================================================
-- MESSAGES
--
-- Preserve normalized inbound-channel information required
-- before AI or customer-context resolution begins.
-- ============================================================

alter table public.messages
add column subject text;


alter table public.messages
add column customer_hint text;


alter table public.messages
add column received_at timestamptz;


update public.messages
set received_at = sent_at
where received_at is null;


alter table public.messages
alter column received_at
set default timezone('utc', now());


alter table public.messages
alter column received_at
set not null;


alter table public.messages
add column attachments jsonb
not null
default '[]'::jsonb;


alter table public.messages
add column channel_metadata jsonb
not null
default '{}'::jsonb;


alter table public.messages
add constraint messages_attachments_must_be_array
check (
    jsonb_typeof(attachments) = 'array'
);


alter table public.messages
add constraint messages_channel_metadata_must_be_object
check (
    jsonb_typeof(channel_metadata) = 'object'
);


create index messages_received_at_idx
on public.messages (
    ticket_id,
    received_at
);


-- ============================================================
-- KEEP TICKET RECENCY SYNCHRONIZED
--
-- New messages should move the ticket's updated_at timestamp so
-- the future agent queue can sort by recent conversation activity.
-- ============================================================

create or replace function public.touch_ticket_from_message()
returns trigger
language plpgsql
set search_path = ''
as $$
begin
    update public.tickets
    set updated_at = greatest(
        updated_at,
        new.received_at
    )
    where id = new.ticket_id;

    return new;
end;
$$;


create trigger messages_touch_ticket
after insert on public.messages
for each row
execute function public.touch_ticket_from_message();