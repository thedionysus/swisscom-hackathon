-- src/swiss_grounding/corpus/schema.sql
-- The corpus schema. Idempotent: `corpus init` runs it on every call.
create extension if not exists vector;
create extension if not exists unaccent;
create schema if not exists corpus;

-- One keyword configuration per language store, each folding accents.
do $$
declare cfg record;
begin
  for cfg in select * from (values
      ('sg_german', 'german', 'german_stem'),
      ('sg_french', 'french', 'french_stem'),
      ('sg_italian', 'italian', 'italian_stem'),
      ('sg_english', 'english', 'english_stem'),
      ('sg_simple', 'simple', 'simple')) as t(name, copy_of, stem)
  loop
    if not exists (select 1 from pg_ts_config where cfgname = cfg.name
                    and cfgnamespace = 'public'::regnamespace) then
      execute format('create text search configuration public.%I (copy = pg_catalog.%I)', cfg.name, cfg.copy_of);
      execute format('alter text search configuration public.%I alter mapping for hword, hword_part, word with unaccent, %I',
                     cfg.name, cfg.stem);
    end if;
  end loop;
end $$;

create or replace function corpus.ts_config(lang text) returns regconfig
language sql immutable as $$
  select (case lang when 'de' then 'public.sg_german' when 'fr' then 'public.sg_french' when 'it' then 'public.sg_italian'
                    when 'en' then 'public.sg_english' else 'public.sg_simple' end)::regconfig
$$;

-- Breadcrumb weighs most, then the description, then the text (weights A, B, C).
create or replace function corpus.chunk_tsv(lang text, crumbs text[], description text, body text) returns tsvector
language sql immutable as $$
  select setweight(to_tsvector(corpus.ts_config(lang), coalesce(array_to_string(crumbs, ' '), '')), 'A')
      || setweight(to_tsvector(corpus.ts_config(lang), coalesce(description, '')), 'B')
      || setweight(to_tsvector(corpus.ts_config(lang), coalesce(body, '')), 'C')
$$;

create table if not exists corpus.source (
  id          text primary key,
  name        text not null,
  publisher   text not null,
  authority   text not null check (authority in
                ('federal_law','cantonal_law','municipal_law','official_info','institutional')),
  level       text not null check (level in ('federal','cantonal','municipal')),
  extent_id   text not null references public.location(id),
  connector   text not null check (connector in ('fedlex','html','json')),
  tier        integer not null,
  languages   text[] not null,
  config      jsonb not null default '{}'
);
-- #55 added the json connector. A database created before that keeps the old check, so replace it here;
-- both statements are idempotent, like the rest of this file.
alter table corpus.source drop constraint if exists source_connector_check;
alter table corpus.source add constraint source_connector_check check (connector in ('fedlex','html','json'));

create table if not exists corpus.translation_group (
  id                   text primary key,
  work_key             text not null unique,
  description_by_lang  jsonb not null default '{}',
  topics               text[] not null default '{}'
);

create table if not exists corpus.document (
  id                    bigserial primary key,
  source_id             text not null references corpus.source(id),
  url                   text not null,
  language              text not null check (language in ('de','fr','it','en','rm')),
  translation_group_id  text not null references corpus.translation_group(id),
  title                 text not null,
  identifier            text,
  publisher             text not null,
  authority             text not null,
  extent_id             text not null references public.location(id),
  is_authentic          boolean not null default true,
  valid_from            date,
  valid_to              date,
  status                text not null check (status in ('current','scheduled','superseded','withdrawn')),
  published_at          date,
  modified_at           date,
  fetched_at            timestamptz not null,
  last_seen_at          timestamptz not null,
  content_hash          text not null,
  extraction            text not null default 'native' check (extraction in ('native','pdf_text','ocr')),
  retrieved_via         text,
  artifact_path         text,
  superseded_by         bigint references corpus.document(id)
);
create unique index if not exists document_live_url on corpus.document(url) where status in ('current','scheduled');
create index if not exists document_group_idx on corpus.document(translation_group_id, language, status);

create sequence if not exists corpus.chunk_id_seq;
create table if not exists corpus.chunk (
  id                    bigint not null default nextval('corpus.chunk_id_seq'),
  document_id           bigint not null references corpus.document(id) on delete cascade,
  language              text not null,
  translation_group_id  text not null,
  align_key             text not null,
  ordinal               integer not null,
  breadcrumb            text[] not null,
  anchor                text,
  text                  text not null,
  description           text not null default '',
  topics                text[] not null default '{}',
  extent_id             text not null,
  authority             text not null,
  status                text not null check (status in ('current','scheduled','superseded','withdrawn','boilerplate')),
  chunk_hash            text not null,
  needs_ocr             boolean not null default false,
  ocr_image             text,
  tsv                   tsvector generated always as (corpus.chunk_tsv(language, breadcrumb, description, text)) stored,
  primary key (id, language)
) partition by list (language);
alter sequence corpus.chunk_id_seq owned by corpus.chunk.id;

create table if not exists corpus.emb_openai_3l (
  chunk_id    bigint not null,
  language    text not null,
  text_hash   text not null,
  embedding   halfvec(3072) not null,
  primary key (chunk_id, language),
  foreign key (chunk_id, language) references corpus.chunk(id, language) on delete cascade
) partition by list (language);

create table if not exists corpus.emb_bge_m3 (
  chunk_id    bigint not null,
  language    text not null,
  text_hash   text not null,
  embedding   vector(1024) not null,
  -- bge-m3's learned sparse (lexical-weight) vector over its multilingual vocabulary.
  -- Null when the dense-only fallback embedded the chunk. At most 1,000 non-zero entries (HNSW limit).
  sparse      sparsevec(250002),
  primary key (chunk_id, language),
  foreign key (chunk_id, language) references corpus.chunk(id, language) on delete cascade
) partition by list (language);

do $$
declare lang text;
begin
  foreach lang in array array['de','fr','it','en','rm'] loop
    execute format('create table if not exists corpus.chunk_%s partition of corpus.chunk for values in (%L)', lang, lang);
    execute format('create table if not exists corpus.emb_openai_3l_%s partition of corpus.emb_openai_3l for values in (%L)', lang, lang);
    execute format('create table if not exists corpus.emb_bge_m3_%s partition of corpus.emb_bge_m3 for values in (%L)', lang, lang);
  end loop;
end $$;

create index if not exists chunk_tsv_idx on corpus.chunk using gin (tsv);
create index if not exists chunk_align_idx on corpus.chunk (translation_group_id, align_key);
create index if not exists chunk_extent_idx on corpus.chunk (extent_id, status);
create index if not exists chunk_document_idx on corpus.chunk (document_id);

-- Index the (text_hash, language) lookup used to reuse embeddings across versions.
create index if not exists emb_openai_3l_hash_idx on corpus.emb_openai_3l (text_hash, language);
create index if not exists emb_bge_m3_hash_idx on corpus.emb_bge_m3 (text_hash, language);

create table if not exists corpus.embedding_index (
  name        text primary key,
  provider    text not null,
  model       text not null,
  dim         integer not null,
  storage     text not null,
  created_at  timestamptz not null default now()
);
insert into corpus.embedding_index (name, provider, model, dim, storage) values
  ('openai-3l', 'openai', 'text-embedding-3-large', 3072, 'halfvec'),
  ('bge-m3', 'local', 'BAAI/bge-m3', 1024, 'vector')
on conflict (name) do nothing;

create table if not exists corpus.fetch_state (
  url            text primary key,
  source_id      text not null references corpus.source(id),
  etag           text,
  last_modified  text,
  content_hash   text not null,
  last_seen_at   timestamptz not null default now()
);

create table if not exists corpus.quarantine (
  id         bigserial primary key,
  source_id  text not null,
  url        text not null,
  stage      text not null,
  reason     text not null,
  attempts   integer not null default 1,
  first_at   timestamptz not null default now(),
  last_at    timestamptz not null default now(),
  unique (source_id, url, stage)
);

create table if not exists corpus.llm_spend (
  id             bigserial primary key,
  kind           text not null,
  model          text not null,
  usd            numeric not null,
  input_tokens   bigint not null default 0,
  output_tokens  bigint not null default 0,
  estimated      boolean not null,
  recorded_at    timestamptz not null default now()
);

create table if not exists corpus.batch_job (
  id             text primary key,
  kind           text not null,
  endpoint       text not null,
  status         text not null,
  request_count  integer not null,
  input_path     text not null,
  estimated_usd  numeric not null,
  created_at     timestamptz not null default now(),
  ingested_at    timestamptz
);
