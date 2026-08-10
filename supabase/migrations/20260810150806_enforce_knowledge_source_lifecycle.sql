-- ============================================================
-- SupportPilot AI
-- M3A — Approved Knowledge Lifecycle
-- ============================================================

-- ------------------------------------------------------------
-- Correct the knowledge_sources timestamp trigger.
--
-- The original generic trigger expects an updated_at column.
-- knowledge_sources uses last_updated instead.
-- ------------------------------------------------------------

drop trigger if exists
    knowledge_sources_set_updated_at
on public.knowledge_sources;


create or replace function
public.set_knowledge_source_last_updated()
returns trigger
language plpgsql
as $$
begin
    new.last_updated := now();
    return new;
end;
$$;


create trigger knowledge_sources_set_last_updated
before update
on public.knowledge_sources
for each row
execute function
public.set_knowledge_source_last_updated();


-- ------------------------------------------------------------
-- Database-level lifecycle guard.
--
-- DRAFT     -> DRAFT or PUBLISHED
-- PUBLISHED -> PUBLISHED or RETIRED
-- RETIRED   -> immutable
--
-- Once published, the approved content identity is frozen.
-- Retirement may only change lifecycle fields.
-- ------------------------------------------------------------

create or replace function
public.enforce_knowledge_source_lifecycle()
returns trigger
language plpgsql
as $$
begin
    if old.status = 'DRAFT' then

        if new.status not in (
            'DRAFT',
            'PUBLISHED'
        ) then
            raise exception
                'Invalid knowledge source transition: % -> %',
                old.status,
                new.status;
        end if;

    elsif old.status = 'PUBLISHED' then

        if new.status not in (
            'PUBLISHED',
            'RETIRED'
        ) then
            raise exception
                'Invalid knowledge source transition: % -> %',
                old.status,
                new.status;
        end if;

        if (
            new.title,
            new.type,
            new.version,
            new.effective_at,
            new.checksum,
            new.created_by,
            new.metadata
        )
        is distinct from
        (
            old.title,
            old.type,
            old.version,
            old.effective_at,
            old.checksum,
            old.created_by,
            old.metadata
        ) then
            raise exception
                'Published knowledge source content is immutable.';
        end if;

    elsif old.status = 'RETIRED' then

        raise exception
            'Retired knowledge sources are immutable.';

    end if;


    if (
        new.status = 'PUBLISHED'
        and new.effective_at is null
    ) then
        raise exception
            'Published knowledge sources require effective_at.';
    end if;


    if (
        new.status = 'RETIRED'
        and new.retired_at is null
    ) then
        raise exception
            'Retired knowledge sources require retired_at.';
    end if;


    if (
        new.status <> 'RETIRED'
        and new.retired_at is not null
    ) then
        raise exception
            'retired_at may only be set for retired sources.';
    end if;


    return new;
end;
$$;


drop trigger if exists
    knowledge_sources_enforce_lifecycle
on public.knowledge_sources;


create trigger knowledge_sources_enforce_lifecycle
before update
on public.knowledge_sources
for each row
execute function
public.enforce_knowledge_source_lifecycle();