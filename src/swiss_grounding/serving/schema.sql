-- Serving-side tables. Idempotent: `serving init` and `setup` run it on every call.
create schema if not exists serving;

create table if not exists serving.call_log (
  id           bigserial primary key,
  tool         text not null,
  started_at   timestamptz not null default now(),
  duration_ms  integer not null,
  status       text not null,
  places       integer not null default 0,
  citations    integer not null default 0,
  reranker     text,
  error        text
);
create index if not exists call_log_tool_idx on serving.call_log (tool, started_at);

-- Last good value of a live lookup, returned with source_unavailable when the source is down.
create table if not exists serving.lookup_cache (
  key             text primary key,
  value           jsonb not null,
  reference_date  date,
  source_url      text not null,
  fetched_at      timestamptz not null default now()
);

create table if not exists serving.premium_region (
  year    integer not null,
  bfs_id  integer not null,
  canton  text not null,
  region  integer not null,
  primary key (year, bfs_id)
);

create table if not exists serving.premium (
  id            bigserial primary key,
  year          integer not null,
  insurer_id    text not null,
  insurer_name  text not null,
  canton        text not null,
  region        integer not null,
  age_class     text not null check (age_class in ('child','young_adult','adult')),
  accident      boolean not null,
  model         text not null check (model in ('standard','family_doctor','hmo','telmed','other')),
  model_label   text not null,
  deductible    integer not null,
  premium_chf   numeric(8,2) not null,
  source_url    text not null
);
create index if not exists premium_lookup_idx
  on serving.premium (year, canton, region, age_class, accident, deductible);
