"""What `as_of` means to `QueryCore`: the boundary, and where the check sits.

`as_of` is two things at once. It replaces `today` for the reranker, which is
`test_query_core_clock.py`; and it restricts which documents are retrievable at all,
which is here. Splitting them is the point -- a file about both was a file about neither.

`QueryCore` is the only layer that can refuse a date, because the earliest answerable
date is a property of the corpus and has to be queried. Everything below drives that
through the public `query` method rather than the helper, so the ordering against the
other outcomes is part of what is pinned.
"""
from datetime import date

from swiss_grounding.retrieval.query_core import QueryCore

# --- `as_of` is refused when the index cannot answer for it ----------------------------
#
# The clock and the filter are the same field seen twice: `as_of` replaces `today` for
# the reranker (above) *and* restricts which documents are retrievable at all. The tests
# below are about the second, and they live here because they are about what `as_of`
# means to `QueryCore`, which is the only place that can refuse it.


def _stub_core(monkeypatch, *, earliest, searched):
    """A QueryCore over an index whose oldest recorded version is `earliest`.

    `searched` is a list the fake `hybrid_search` appends to, because a refused `as_of`
    must be refused *instead of* searching rather than alongside a search whose result is
    discarded -- the refusal exists to stop the server answering an unanswerable question.
    """
    from swiss_grounding.locations.models import Level, Location, ResolvedLocation
    from swiss_grounding.locations.tree import LocationTree
    from swiss_grounding.retrieval import query_core
    from swiss_grounding.retrieval.rerank import RerankWeights

    tree = LocationTree.from_locations([Location(id="CH", parent_id=None, level=Level.COUNTRY, bfs_id=None,
                                                 lindas_uri=None, names={"en": "Switzerland"}, aliases=())])

    class Resolver:
        def resolve(self, text):
            return ResolvedLocation(location=tree.get("CH"), path=("CH",), method="alias", input_text=text)

    class Cursor:
        # One stub for two different single-row queries: the boundary lookup and, on the
        # empty path these tests all take, the `PathEvidence` census. A census of zeroes
        # is the honest reading of "the fake search returned nothing".
        def fetchall(self): return []
        def fetchone(self):
            return {"earliest": earliest, "chunks_without_as_of": 0,
                    "chunks_without_topics": 0, "earliest_valid_from": earliest}

    class Conn:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def execute(self, *a, **k): return Cursor()

    def fake_search(*a, **k):
        searched.append(k.get("as_of"))
        return ()

    monkeypatch.setattr(query_core, "connect", lambda url: Conn())
    monkeypatch.setattr(query_core, "hybrid_search", fake_search)
    return QueryCore(database_url="x", tree=tree, resolver=Resolver(), embedder=None,
                     weights=RerankWeights(), today=lambda: date(2026, 9, 16))


def test_as_of_before_the_earliest_indexed_version_is_refused_not_silently_filtered(monkeypatch):
    """The defect this guards against: only current consolidations are indexed, so `as_of` 2020
    excluded every act and returned the undated pages that bypassed the filter, as the
    answer to a question about 2020. Refusing names the boundary the caller can move to."""
    from swiss_grounding.retrieval.models import QueryRequest

    searched: list = []
    core = _stub_core(monkeypatch, earliest=date(2023, 9, 1), searched=searched)

    resp = core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",),
                                   as_of=date(2020, 1, 1)))

    assert resp.status == "invalid_request"
    assert resp.field == "as_of"
    assert "2023-09-01" in resp.message
    assert searched == []


def test_an_as_of_the_index_can_answer_for_still_searches(monkeypatch):
    """The refusal is a boundary check, not a ban: the dated path must keep working."""
    from swiss_grounding.retrieval.models import QueryRequest

    searched: list = []
    core = _stub_core(monkeypatch, earliest=date(2023, 9, 1), searched=searched)

    resp = core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",),
                                   as_of=date(2026, 9, 8)))

    assert resp.status != "invalid_request"
    assert searched == [date(2026, 9, 8)]


def test_an_index_with_no_dated_document_refuses_every_as_of(monkeypatch):
    from swiss_grounding.retrieval.models import QueryRequest

    searched: list = []
    core = _stub_core(monkeypatch, earliest=None, searched=searched)

    resp = core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",),
                                   as_of=date(2026, 9, 8)))

    assert resp.status == "invalid_request"
    assert resp.field == "as_of"
    assert searched == []


def test_a_request_without_as_of_never_consults_the_index_for_a_boundary(monkeypatch):
    """`_validate` is pure and pre-database by design. The boundary is the one thing that
    cannot be, so it is paid for only by the requests that carry a date."""
    from swiss_grounding.retrieval.models import QueryRequest

    searched: list = []
    core = _stub_core(monkeypatch, earliest=None, searched=searched)

    resp = core.query(QueryRequest(question="q", location="Switzerland", topics=("waste",)))

    assert resp.status != "invalid_request"
    assert searched == [None]


def test_a_refused_as_of_is_reported_before_an_unresolvable_location(monkeypatch):
    """`as_of` is a request field, and an unanswerable one is unanswerable whatever the
    location resolves to. Reporting `needs_location` first would send the caller round a
    loop fixing the place, only to be refused on the date afterwards."""
    from swiss_grounding.retrieval.models import QueryRequest

    searched: list = []
    core = _stub_core(monkeypatch, earliest=date(2023, 9, 1), searched=searched)

    resp = core.query(QueryRequest(question="q", location="", topics=("waste",),
                                   as_of=date(2020, 1, 1)))

    assert resp.status == "invalid_request"
    assert resp.field == "as_of"
