"""Local topic classifier: the fallback when the caller supplies no topic (ADR 0004).

`swiss_search` treats topic as a hard filter, and ADR 0004 makes the calling model the
primary source of it — the server cannot translate or interpret intent at query time
without an API call, which the offline guarantee forbids. When a caller supplies none,
this module estimates it locally: embed the question with the same Embedder already
loaded for search, and compare it against the ten category descriptions embedded once.

Similarity measure: cosine similarity via dot product. The Embedder protocol's contract
is unit-norm output (see FakeEmbedder's explicit normalisation and
SentenceTransformerEmbedder's normalize_embeddings=True), so `a @ b` on two of its
outputs is the cosine similarity, not merely proportional to it — with one caveat:
FakeEmbedder returns the zero vector, not a unit vector, for text with no matching
token (`embedder.py`'s `vec / norm if norm > 0 else vec`). This is safe here because
it can only make every similarity 0.0, which sits under TOPIC_FLOOR and returns no
topics — the same degrade-to-nothing behaviour a genuinely unrelated question gets —
and the category descriptions themselves always contain tokens, so only a pathological
*question* could hit it, never the category side of the comparison. Higher is better
and the range is [-1, 1]. `search.py`'s pgvector `<=>` operator is cosine *distance*
(1 - similarity, lower is better) over the same normalised vectors — the two are the
same geometry read in opposite directions, so TOPIC_FLOOR and TOPIC_MARGIN below are
honest against it once "higher is better" is kept straight.

ADR 0004 also records why the margin band exists rather than picking the single best
category: matching a German question against English descriptions is uneven —
`Leinenpflicht` landed on `hiking` ahead of `dogs` by a similarity margin of only 0.008,
and `Grüngutabfuhr` only cleared its category by 0.032. A near-tie is evidence the
classifier cannot tell the categories apart for this question, not evidence for the
top-ranked one, so every category within TOPIC_MARGIN of the best is kept rather than
just the winner — except when the band itself saturates (see TOPIC_MAX_TOPICS).
"""

from functools import cache

import numpy as np

from swiss_grounding.registry.categories import CATEGORIES
from swiss_grounding.retrieval.embedder import Embedder
from swiss_grounding.retrieval.models import QueryRequest

# Below this cosine similarity, the best-matching category is not a confident match —
# return no topics so an unrecognised question degrades to no filter (search still runs
# on the extent path alone) rather than being pinned to a wrong one.
#
# The plan supplied 0.45. Measured against a 23-question corpus spanning all ten
# categories (English and German, including compounds), the worst genuine on-topic
# question — "Krankenkassenprämie" ("health insurance premium"), a single German
# compound noun with no other context — scored 0.4535 against `health`: only 0.0035
# above the plan's floor. One word of rewording would have put a legitimate question
# below it and silently returned no topics. Moved to 0.42 for real headroom (0.0335 on
# that same case) rather than leaving the constant sitting on the edge of the first
# on-topic case that happened to get measured.
#
# This does not make the floor alone safe: on the same corpus, two out-of-scope
# questions ("Tell me about Hamlet", a plain English sentence with no Swiss-admin
# content, and "Einbürgerung Voraussetzungen", a real Swiss-admin topic outside the ten
# categories) clear 0.42 at 0.4466 and 0.4842 respectively — the second one even clears
# the *old* 0.45. Both are caught downstream by TOPIC_MAX_TOPICS instead: a question the
# classifier cannot really place tends to land close to several categories at once
# rather than confidently on one, so the saturation cap is what actually keeps them from
# being reported as classified. The floor and the cap are a pair, not two independent
# guards — see TOPIC_MAX_TOPICS's docstring.
TOPIC_FLOOR = 0.42

# Any category within this many cosine-similarity points of the best is kept alongside
# it, not discarded, because bge-m3's cross-lingual matching is uneven enough that the
# true topic and a runner-up can sit this close together (see module docstring). Widening
# the band trades precision for recall; 0.10 is the plan's measured value, not tuned here.
TOPIC_MARGIN = 0.10

# When more than this many categories fall within TOPIC_MARGIN of the best, the band has
# saturated: the classifier has no opinion, not a confident multi-topic match, and must
# say so by returning no topics rather than a wide one. This matters once topic is a hard
# filter (Task 8) — CONTEXT.md records that a chunk may legitimately carry no topics and
# is accepted as invisible under a hard filter, so a nine-of-ten-category result still
# excludes every untagged chunk exactly as one category would, while an empty result
# skips the filter and keeps them. A caller cannot tell "confidently these two" from
# "could be any of nine" unless the classifier itself makes that distinction.
#
# Measured on the same 23-question corpus, band sizes were 1 for 12 questions, 2 for 5,
# 3 for 1 (dogs+hiking questions genuinely straddle two categories) — then a clear jump
# to 4, 6, 8 and 8 for the rest, all of them either genuinely ambiguous ("When does the
# next tram depart?") or out-of-scope questions the floor alone let through (see
# TOPIC_FLOOR). 1–3 is the shape of a real answer; anything wider is the shape of no
# answer, so 3 is the cutoff.
TOPIC_MAX_TOPICS = 3


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


def classify_topics(question: str, embedder: Embedder) -> tuple[str, ...]:
    """Estimate the question's topic(s) from category description similarity.

    Returns every category within TOPIC_MARGIN of the best cosine similarity, sorted for
    determinism, unless the best similarity is below TOPIC_FLOOR or the band has more
    than TOPIC_MAX_TOPICS categories in it — either way an unrecognised or ambiguous
    question degrades to no topic filter rather than a wrong or meaninglessly wide one.

    Raises ValueError on an empty or whitespace-only question: every category sits
    equally, meaninglessly close to a vector with nothing in it, so "classify nothing"
    is a caller error to reject, not a result to return. query_core.py already rejects
    empty questions before this is reached in the running server, but classify_topics is
    a public function with no other guard documented as sitting in front of it.
    """
    if not question.strip():
        raise ValueError("question must not be empty")
    [question_vector] = embedder.embed([question])
    similarities = {
        category_id: float(question_vector @ category_vector)
        for category_id, category_vector in _category_vectors(embedder)
    }
    best = max(similarities.values())
    if best < TOPIC_FLOOR:
        return ()
    band = tuple(
        sorted(category_id for category_id, score in similarities.items() if score >= best - TOPIC_MARGIN)
    )
    if len(band) > TOPIC_MAX_TOPICS:
        return ()
    return band


def resolve_topics(request: QueryRequest, embedder: Embedder) -> tuple[str, ...]:
    """Decide what `swiss_search` filters on for this request, in ADR 0004's order.

    1. `request.topics` -- the caller said what the question is about. ADR 0004 makes the
       calling model the primary source: it reads the user's question, it already speaks
       the user's language, and it is paying for its own tokens.
    2. `request.categories` -- the same caller, on the older contract. It is the only way
       a client that has not been updated can state a subject at all, and an explicit
       statement from the caller must outrank a guess made on its behalf. This rung
       disappears when Task 10 replaces the tool contract; until then, dropping it would
       mean ignoring what the caller said in favour of what the server guessed.
    3. `classify_topics` -- the local fallback, used only when the caller said nothing.

    Returns sorted ids so the applied filter is deterministic whatever PYTHONHASHSEED is
    (ADR 0004 commits probes to determinism), and an empty tuple to mean *no constraint*
    -- which is not the same as a constraint nothing satisfies. `search.FILTER` documents
    what that distinction costs if it is lost.

    Raises ValueError on an empty question, from `classify_topics`. `query_core._validate`
    rejects those before this is reached, so an exception here is a programming error in
    a new caller rather than a user error to render.
    """
    if request.topics:
        return tuple(sorted(set(request.topics)))
    if request.categories:
        return tuple(sorted(set(request.categories)))
    return classify_topics(request.question, embedder)
