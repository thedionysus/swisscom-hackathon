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
    llm_tagging        boolean not null default true,
    license            text,
    origin             text not null default 'seed' check (origin in ('seed','auto_approved','reviewed'))
);
-- Databases created before this column existed pick it up on the next db init.
alter table source add column if not exists llm_tagging boolean not null default true;

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
    event_date      date,
    published_at    timestamptz,
    retrieved_at    timestamptz not null default now(),
    content_hash    text not null,
    version         integer not null default 1,
    superseded_by   bigint references document(id),
    status          text not null default 'current' check (status in ('current','superseded','withdrawn','pending_enrichment')),
    -- 'crawl' for documents fetched from the source, 'fixture' for offline demo data
    origin          text not null default 'crawl' check (origin in ('crawl','fixture'))
);
-- Databases created before these columns existed pick them up on the next db init.
alter table document add column if not exists event_date date;
alter table document add column if not exists origin text not null default 'crawl';
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
    -- Generated description of what the document is about and what this chunk covers.
    -- Indexed with the text, never cited: `retrieval/cite.py` reads text_en and text_original only.
    context_en       text not null default '',
    embedding        vector({{EMBEDDING_DIM}}) not null,
    -- `tsv` is deliberately absent here: the guarded block below is its sole definition, for
    -- both a database created from scratch and one carried forward. Written in two places it
    -- could be edited in one, which is the divergence the block itself exists to prevent.
    chunk_hash       text not null,
    extent_id        text not null references location(id),
    authority        text not null check (authority in
        ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
    categories       text[] not null default '{}',
    -- denormalized copy, kept for now but never used as a query filter; document.status wins
    document_status  text not null default 'current' check (document_status in
        ('current','superseded','withdrawn','pending_enrichment'))
);
-- Databases created before this column existed pick it up on the next db init.
alter table chunk add column if not exists context_en text not null default '';

-- The one definition of `tsv`, which must cover the generated context as well as the text.
-- It is here rather than inline in `create table` because `create table if not
-- exists` skips an existing table: an inline definition would reach databases created from
-- scratch and never the one already holding the corpus. A generated column cannot be altered
-- in place, so an existing one is dropped and rebuilt -- which also drops `chunk_tsv_idx`,
-- defined over it, recreated below.
--
-- The guard reads the column's own stored expression rather than merely checking that `tsv`
-- exists: on a database carried forward the column exists in both the old and the new shape,
-- and only the expression tells them apart. A database already on the new definition falls
-- through untouched, which is what keeps `db init` idempotent -- rebuilding on every run would
-- rewrite the whole table each time.
--
-- It is a substring test, so it carries a database across the one change it was written for and
-- no other: a later definition that still mentions `context_en` will not trigger a rebuild, and
-- whoever makes that change has to widen this test with it.
do $$
declare
    stored_definition text;
begin
    select pg_get_expr(ad.adbin, ad.adrelid) into stored_definition
    from pg_attribute a
    join pg_attrdef ad on ad.adrelid = a.attrelid and ad.adnum = a.attnum
    where a.attrelid = 'chunk'::regclass and a.attname = 'tsv' and a.attgenerated = 's';

    if stored_definition is null or stored_definition not like '%context_en%' then
        alter table chunk drop column if exists tsv;
        alter table chunk add column tsv tsvector generated always as
            (to_tsvector('english', btrim(context_en || ' ' || text_en))) stored;
    end if;
end $$;

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

-- One row per (run, source): the ingest report that the CLI prints, kept so coverage can show fetch health.
create table if not exists ingest_run (
    run_id       text not null,
    source_id    text not null references source(id),
    started_at   timestamptz not null,
    finished_at  timestamptz not null,
    added        integer not null default 0,
    modified     integer not null default 0,
    unchanged    integer not null default 0,
    withdrawn    integer not null default 0,
    -- fetched and enriched, but held nothing worth indexing: neither a success nor a failure
    skipped      integer not null default 0,
    failed       integer not null default 0,
    primary key (run_id, source_id)
);
alter table ingest_run add column if not exists skipped integer not null default 0;
create index if not exists ingest_run_source_idx on ingest_run(source_id, finished_at desc);

-- One row per probe per eval run. observed is the probe's Observed block as JSON.
create table if not exists eval_run (
    id             bigserial primary key,
    run_id         text not null,
    ran_at         timestamptz not null default now(),
    git_commit     text,
    tier           text not null,
    probe_id       text not null,
    kind           text not null,
    failure_class  text not null,
    passed         boolean not null,
    failures       jsonb not null default '[]',
    observed       jsonb not null default '{}'
);
create index if not exists eval_run_run_idx on eval_run(run_id, tier, probe_id);
