-- src/swiss_grounding/db/schema.sql
create extension if not exists vector;

create table if not exists location (
    id          text primary key,
    parent_id   text references location(id),
    level       text not null check (level in ('country','canton','municipality','neighborhood')),
    bfs_id      integer,
    lindas_uri  text,
    names       jsonb not null,
    path        text[] not null
);
create index if not exists location_path_idx on location using gin (path);

create table if not exists source (
    id                 text primary key,
    name               text not null,
    base_url           text not null,
    default_extent_id  text not null references location(id),
    authority          text not null check (authority in
        ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
    categories         text[] not null default '{}',
    fetch_strategy     text not null,
    fetch_config       jsonb not null default '{}',
    allow_narrowing    boolean not null default false,
    license            text,
    origin             text not null default 'seed' check (origin in ('seed','auto_approved','reviewed'))
);

create table if not exists source_suggestion (
    id                   bigserial primary key,
    url                  text not null unique,
    reason               text not null,
    proposed_extent_id   text references location(id),
    proposed_authority   text,
    proposed_categories  text[] not null default '{}',
    domain_class         text not null check (domain_class in ('official','swiss','other')),
    status               text not null default 'pending' check (status in ('pending','approved','rejected')),
    suggested_by         text,
    suggested_at         timestamptz not null default now(),
    reviewed_by          text,
    reviewed_at          timestamptz,
    review_note          text,
    source_id            text references source(id)
);

create table if not exists document (
    id              bigserial primary key,
    source_id       text not null references source(id),
    url             text not null,
    identifier      text,
    title_original  text not null,
    title_en        text not null,
    language        text not null,
    extent_id       text not null references location(id),
    extent_reason   text not null default 'source_default',
    authority       text not null check (authority in
        ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
    categories      jsonb not null default '[]',
    valid_from      date,
    valid_to        date,
    in_force        boolean,
    published_at    timestamptz,
    retrieved_at    timestamptz not null default now(),
    content_hash    text not null,
    version         integer not null default 1,
    superseded_by   bigint references document(id),
    status          text not null default 'current' check (status in ('current','superseded','withdrawn','pending_enrichment'))
);
create index if not exists document_url_idx on document(url);
create index if not exists document_status_idx on document(status);

create table if not exists chunk (
    id               bigserial primary key,
    document_id      bigint not null references document(id) on delete cascade,
    ordinal          integer not null,
    text_original    text not null,
    text_en          text not null,
    heading_path     text not null default '',
    anchor           text,
    embedding        vector({{EMBEDDING_DIM}}) not null,
    tsv              tsvector generated always as (to_tsvector('english', text_en)) stored,
    chunk_hash       text not null,
    extent_id        text not null references location(id),
    authority        text not null check (authority in
        ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
    categories       text[] not null default '{}',
    -- denormalized copy, kept for now but never used as a query filter; document.status wins
    document_status  text not null default 'current' check (document_status in
        ('current','superseded','withdrawn','pending_enrichment'))
);
create index if not exists chunk_extent_idx on chunk(extent_id, document_status);
create index if not exists chunk_tsv_idx on chunk using gin (tsv);
create index if not exists chunk_embedding_idx on chunk using hnsw (embedding vector_cosine_ops);

create table if not exists document_change (
    id                    bigserial primary key,
    run_id                text not null,
    document_id           bigint references document(id),
    previous_document_id  bigint references document(id),
    change_type           text not null check (change_type in ('added','modified','withdrawn')),
    chunks_added          bigint[] not null default '{}',
    chunks_removed        bigint[] not null default '{}',
    chunks_modified       bigint[] not null default '{}',
    changed_at            timestamptz not null default now()
);

create table if not exists fetch_state (
    url            text primary key,
    source_id      text not null references source(id),
    etag           text,
    last_modified  text,
    content_hash   text not null,
    last_seen_at   timestamptz not null default now()
);
create index if not exists fetch_state_source_idx on fetch_state(source_id);
