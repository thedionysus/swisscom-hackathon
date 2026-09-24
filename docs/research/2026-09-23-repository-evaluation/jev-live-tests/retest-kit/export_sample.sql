-- Labelling sample from the corpus, with the production topics as a baseline.
-- Run: psql "$DATABASE_URL" -At -f export_sample.sql > chunks_with_baseline.json
-- Columns: corpus/schema.sql:62-105 (document.title, chunk.breadcrumb, chunk.topics, chunk.status).
-- Only chunks the paid describe stage has processed (description <> ''), so production topics are its own.
-- The order is a fixed hash, not random(), so the same database gives the same sample.
-- Stratify by editing the per-authority limits; aim for at least 100 non-boilerplate chunks overall.
select json_agg(t) from (
  select * from (
    select c.id::text || ':' || c.language as id,
           c.language,
           d.title as page_title,
           array_to_string(c.breadcrumb, ' > ') as heading,
           left(c.text, 2500) as text,                      -- describe shows the model 2500 chars (describe.py:29)
           c.topics as production_topics,
           (c.status = 'boilerplate') as production_boilerplate,
           c.authority,
           row_number() over (partition by c.authority order by md5(c.id::text || c.language || 'fresh-sample-v1')) as rn
    from corpus.chunk c
    join corpus.document d on d.id = c.document_id
    where c.status in ('current', 'scheduled', 'boilerplate')
      and c.description <> ''
  ) s
  where rn <= 40                                             -- up to 40 per authority level
) t;
