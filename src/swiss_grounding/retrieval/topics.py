"""Local topic classifier: the fallback when the caller supplies no topic (ADR 0004).

`swiss_search` treats topic as a hard filter, and ADR 0004 makes the calling model the
primary source of it — the server cannot translate or interpret intent at query time
without an API call, which the offline guarantee forbids. When a caller supplies none,
this module estimates it locally: embed the question with the same Embedder already
loaded for search, and compare it against the ten category descriptions embedded once.

Similarity measure: cosine similarity via dot product. The Embedder protocol returns
unit-norm vectors (see FakeEmbedder's explicit normalisation and
SentenceTransformerEmbedder's normalize_embeddings=True), so `a @ b` on two of its
outputs already *is* the cosine similarity, not merely proportional to it. Higher is
better and the range is [-1, 1]. `search.py`'s pgvector `<=>` operator is cosine
*distance* (1 - similarity, lower is better) over the same normalised vectors — the two
are the same geometry read in opposite directions, so TOPIC_FLOOR and TOPIC_MARGIN below
are honest against it once "higher is better" is kept straight.

ADR 0004 also records why the two constants exist rather than picking the single best
category: matching a German question against English descriptions is uneven —
`Leinenpflicht` landed on `hiking` ahead of `dogs` by a similarity margin of only 0.008,
and `Grüngutabfuhr` only cleared its category by 0.032. A near-tie is evidence the
classifier cannot tell the categories apart for this question, not evidence for the
top-ranked one, so every category within TOPIC_MARGIN of the best is kept rather than
just the winner.
"""

from functools import cache

import numpy as np

from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.retrieval.embedder import Embedder

# Below this cosine similarity, the best-matching category is not a confident match —
# return no topics so an unrecognised question degrades to no filter (search still runs
# on the extent path alone) rather than being pinned to a wrong one. Measured against the
# real bge-m3 embedder: the four on-topic probe questions all clear it comfortably, and
# an unrelated question ("What is the capital of Peru?") falls under it.
TOPIC_FLOOR = 0.45

# Any category within this many cosine-similarity points of the best is kept alongside
# it, not discarded, because bge-m3's cross-lingual matching is uneven enough that the
# true topic and a runner-up can sit this close together (see module docstring). Widening
# the band trades precision for recall; 0.10 is the plan's measured value, not tuned here.
TOPIC_MARGIN = 0.10


@cache
def _category_vectors(embedder: Embedder) -> tuple[tuple[str, np.ndarray], ...]:
    """The ten category descriptions embedded once per Embedder instance.

    Memoised on the embedder object itself (identity-hashed, since Embedder
    implementations define no custom __eq__/__hash__): the first call for a given
    embedder pays the embedding cost, every later call in the same process — same
    Embedder loaded once at startup — reuses it. This satisfies "embed once at startup"
    without forcing every caller of classify_topics to thread a separate classifier
    object through the MCP tool handler on each request.
    """
    texts = [f"{c.label}. {c.description}" for c in CATEGORIES]
    vectors = embedder.embed(texts)
    return tuple(zip((c.id for c in CATEGORIES), vectors, strict=True))


def classify_topics(question: str, embedder: Embedder) -> frozenset[str]:
    """Estimate the question's topic(s) from category description similarity.

    Returns every category within TOPIC_MARGIN of the best cosine similarity, or an
    empty set if the best similarity is below TOPIC_FLOOR — an unrecognised question
    degrades to no topic filter rather than a wrong one.
    """
    [question_vector] = embedder.embed([question])
    similarities = {
        category_id: float(question_vector @ category_vector)
        for category_id, category_vector in _category_vectors(embedder)
    }
    best = max(similarities.values())
    if best < TOPIC_FLOOR:
        return frozenset()
    return frozenset(
        category_id for category_id, score in similarities.items() if score >= best - TOPIC_MARGIN
    )
