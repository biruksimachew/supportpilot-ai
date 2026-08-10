-- ============================================================
-- SupportPilot AI
-- M3B — Deterministic Knowledge Embeddings
-- ============================================================


-- ------------------------------------------------------------
-- Existing M1/M3A data intentionally has NULL embeddings.
-- Refuse migration if unexpected vectors already exist because
-- silently coercing vectors of an unknown dimension is unsafe.
-- ------------------------------------------------------------

do $$
begin
    if exists (
        select 1
        from public.knowledge_chunks
        where embedding is not null
    ) then
        raise exception
            'Cannot lock embedding dimension while existing vectors are present.';
    end if;
end;
$$;


-- ------------------------------------------------------------
-- Lock pgvector to our chosen embedding contract.
-- ------------------------------------------------------------

alter table public.knowledge_chunks
    alter column embedding
    type extensions.vector(1536)
    using embedding::extensions.vector(1536);


-- ------------------------------------------------------------
-- Persist enough provenance to reproduce and verify every
-- indexed chunk.
-- ------------------------------------------------------------

alter table public.knowledge_chunks
    add column if not exists
        content_checksum text,

    add column if not exists
        index_fingerprint text,

    add column if not exists
        embedding_provider text,

    add column if not exists
        embedding_model text,

    add column if not exists
        embedding_dimensions integer,

    add column if not exists
        embedded_at timestamp with time zone;


alter table public.knowledge_chunks
    drop constraint if exists
        knowledge_chunks_content_checksum_check,

    add constraint
        knowledge_chunks_content_checksum_check
    check (
        content_checksum is null
        or content_checksum ~ '^[0-9a-f]{64}$'
    );


alter table public.knowledge_chunks
    drop constraint if exists
        knowledge_chunks_index_fingerprint_check,

    add constraint
        knowledge_chunks_index_fingerprint_check
    check (
        index_fingerprint is null
        or index_fingerprint ~ '^[0-9a-f]{64}$'
    );


alter table public.knowledge_chunks
    drop constraint if exists
        knowledge_chunks_embedding_dimensions_check,

    add constraint
        knowledge_chunks_embedding_dimensions_check
    check (
        embedding_dimensions is null
        or embedding_dimensions = 1536
    );


alter table public.knowledge_chunks
    drop constraint if exists
        knowledge_chunks_embedding_state_check,

    add constraint
        knowledge_chunks_embedding_state_check
    check (
        (
            embedding is null
            and content_checksum is null
            and index_fingerprint is null
            and embedding_provider is null
            and embedding_model is null
            and embedding_dimensions is null
            and embedded_at is null
        )
        or
        (
            embedding is not null
            and content_checksum is not null
            and index_fingerprint is not null
            and embedding_provider is not null
            and embedding_model is not null
            and embedding_dimensions = 1536
            and embedded_at is not null
        )
    );


create index if not exists
    knowledge_chunks_index_fingerprint_idx
on public.knowledge_chunks (
    index_fingerprint
);


create index if not exists
    knowledge_chunks_embedding_model_idx
on public.knowledge_chunks (
    embedding_provider,
    embedding_model,
    embedding_dimensions
);


-- ------------------------------------------------------------
-- If draft content is modified, any existing embedding must
-- become invalid automatically.
--
-- Published content remains immutable while embedding metadata
-- may still be updated by the indexing pipeline.
-- ------------------------------------------------------------

create or replace function
public.guard_knowledge_chunk_content_update()
returns trigger
language plpgsql
as $$
declare
    source_status text;
begin
    if (
        new.source_id,
        new.section,
        new.content,
        new.metadata
    )
    is distinct from
    (
        old.source_id,
        old.section,
        old.content,
        old.metadata
    ) then

        select status
        into source_status
        from public.knowledge_sources
        where id = old.source_id;

        if source_status <> 'DRAFT' then
            raise exception
                'Published or retired knowledge content is immutable.';
        end if;

        new.embedding := null;
        new.content_checksum := null;
        new.index_fingerprint := null;
        new.embedding_provider := null;
        new.embedding_model := null;
        new.embedding_dimensions := null;
        new.embedded_at := null;
    end if;

    return new;
end;
$$;


drop trigger if exists
    knowledge_chunks_guard_content_update
on public.knowledge_chunks;


create trigger
    knowledge_chunks_guard_content_update
before update
on public.knowledge_chunks
for each row
execute function
    public.guard_knowledge_chunk_content_update();