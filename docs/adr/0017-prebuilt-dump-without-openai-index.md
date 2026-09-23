---
status: accepted
date: 2026-09-23
---

# Setup downloads a prebuilt pg_dump without the OpenAI index and rebuilds vector indexes locally

The rules allow a prebuilt index when setup downloads it with no manual step and the build script is in the repository. Serving is keyless on bge-m3 (ADR 0006), so the evaluators do not need the OpenAI `halfvec(3072)` vectors, which are the largest part of the database.

- The default release asset is a compressed `pg_dump` (custom format) of the corpus with the bge-m3 dense and sparse tables and the premium table. The OpenAI embedding table is a separate, optional asset.
- The dump is a release asset of our **private** repository (decided 2026-09-23): it republishes text crawled from cantonal and municipal sites, and we do not redistribute that publicly. Evaluators are given read access to the repository; `setup` downloads with `gh release download` under their own GitHub login.
- Each asset stays under GitHub's 2 GiB per-file release limit, split if needed, and has a SHA-256 checksum. Git itself refuses files over 100 MB, which is why the dump is a release asset rather than a committed file.
- `setup` downloads, verifies, restores, and rebuilds the vector indexes. The rebuild time is measured after the encoding run and stated in the README.

## Considered Options

- A copy of the Postgres data directory: no index rebuild, but tied to the exact Postgres and pgvector version and to the CPU architecture of an unknown evaluator machine.
- Including the OpenAI index by default: doubles the download for a path that needs a key at query time.
