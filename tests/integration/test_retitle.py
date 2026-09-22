"""Repairing the stored titles of Fedlex acts from the SPARQL endpoint (Task 6, step 2b).

The five stored acts are titled `SR 455` and one carries no title at all, and no re-ingest
repairs that: the fetcher short-circuits on the URL, `persist` compares a content hash that
excludes titles, and nothing else writes one. `recontext` quotes the title into every chunk it
describes, so this must run first -- which is why it is its own command, with its own report.

The endpoint is stubbed here. What it returns is the shape a real SPARQL result has, verified
against the live endpoint: `{"title": {"value": "Tierschutzgesetz vom 16. Dezember 2005 (TSchG)"}}`.
"""

import os
from pathlib import Path

import pytest

from swiss_grounding.db.connection import connect
from swiss_grounding.db.migrate import apply_schema
from swiss_grounding.ingest.fixture_loader import load_fixture
from swiss_grounding.ingest.llm import FakeLLM
from swiss_grounding.ingest.retitle import TitleChange, retitle_all
from swiss_grounding.locations.repository import upsert_locations
from swiss_grounding.locations.seed import seed_locations
from swiss_grounding.registry.loader import load_seed_sources
from swiss_grounding.registry.repository import upsert_sources
from swiss_grounding.retrieval.embedder import FakeEmbedder

pytestmark = pytest.mark.integration
FIXTURE = Path(__file__).parent.parent / "fixtures" / "zurich_hiking.json"
TSCHG = "Tierschutzgesetz vom 16. Dezember 2005 (TSchG)"
ANIMAL_WELFARE_URL = "https://www.fedlex.admin.ch/eli/cc/2008/414/de"
HIKING_URL = "https://www.fedlex.admin.ch/eli/cc/1991/1052_1052_1052/de"


@pytest.fixture
def url():
    u = os.environ["DATABASE_URL"]
    apply_schema(u, embedding_dim=8)
    with connect(u) as conn:
        conn.execute("truncate chunk, document_change, document restart identity cascade")
        upsert_locations(conn, seed_locations())
        upsert_sources(conn, load_seed_sources())
        load_fixture(conn, FIXTURE, FakeEmbedder(dim=8))
        # The two stored Fedlex acts as the backfill finds them: titled by their SR number, and
        # identified the way `fedlex._sr_label` writes it. SR 704 is deliberately one the source
        # no longer lists.
        conn.execute("update document set identifier = 'SR 455', title_original = 'SR 455', "
                     "title_en = 'SR 455' where url = %s", (ANIMAL_WELFARE_URL,))
        conn.execute("update document set identifier = 'SR 704', title_original = 'SR 704', "
                     "title_en = 'SR 704' where url = %s", (HIKING_URL,))
    return u


class StubEndpoint:
    """The SPARQL endpoint's answers, and a record of what was asked of it."""

    def __init__(self, titles: dict[str, str | None], empty: tuple[str, ...] = ()):
        self.titles = titles
        self.empty = empty
        self.asked: list[tuple[str, str]] = []

    def current_consolidation(self, sr: str, lang: str):
        self.asked.append((sr, lang))
        if sr in self.empty:
            return None
        title = self.titles.get(sr)
        return {"title": {"value": title}} if title else {}


class TranslatingLLM(FakeLLM):
    """Records every translation asked for, because each one is a paid call."""

    def __init__(self, breaks_on: str | None = None):
        self.translated: list[str] = []
        self._breaks_on = breaks_on

    def translate(self, text, source_language):
        if text == self._breaks_on:
            raise RuntimeError(f"no credit left for {text!r}")
        self.translated.append(text)
        return f"English: {text}"


def _titles(conn, document_url: str) -> tuple[str, str]:
    row = conn.execute(
        "select title_original, title_en from document where url = %s", (document_url,)).fetchone()
    return row["title_original"], row["title_en"]


def test_retitle_replaces_the_sr_number_with_the_acts_name(url):
    endpoint = StubEndpoint({"455": TSCHG})
    llm = TranslatingLLM()
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, llm)
        stored = _titles(conn, ANIMAL_WELFARE_URL)

    assert stored == (TSCHG, f"English: {TSCHG}")
    assert llm.translated == [TSCHG]
    assert ("455", "de") in endpoint.asked
    assert report.changes == (TitleChange(identifier="SR 455", before="SR 455", after=TSCHG),)
    assert report.updated == 1


def test_a_document_whose_sr_number_the_source_no_longer_lists_is_skipped(url):
    endpoint = StubEndpoint({"455": TSCHG})
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, TranslatingLLM())
        stored = _titles(conn, HIKING_URL)

    assert stored == ("SR 704", "SR 704")
    assert [sr for sr, _ in endpoint.asked] == ["455"]
    assert report.skipped == 1
    assert report.examined == 2


def test_a_title_the_endpoint_does_not_name_is_a_failure_that_changes_nothing(url):
    endpoint = StubEndpoint({"455": None})
    llm = TranslatingLLM()
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, llm)
        stored = _titles(conn, ANIMAL_WELFARE_URL)

    assert stored == ("SR 455", "SR 455")
    assert llm.translated == []
    assert report.failed == 1
    assert report.errors[0].url == ANIMAL_WELFARE_URL
    assert "title" in report.errors[0].reason


def test_an_empty_sparql_result_is_a_failure_that_changes_nothing(url):
    endpoint = StubEndpoint({}, empty=("455",))
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, TranslatingLLM())
        stored = _titles(conn, ANIMAL_WELFARE_URL)

    assert stored == ("SR 455", "SR 455")
    assert report.failed == 1
    assert "no current consolidation" in report.errors[0].reason


def test_a_title_already_repaired_is_not_translated_again(url):
    with connect(url) as conn:
        conn.execute("update document set title_original = %s, title_en = %s where url = %s",
                     (TSCHG, f"English: {TSCHG}", ANIMAL_WELFARE_URL))

    llm = TranslatingLLM()
    with connect(url) as conn:
        report = retitle_all(conn, StubEndpoint({"455": TSCHG}), llm)

    assert llm.translated == []
    assert report.updated == 0
    assert report.skipped == 2


def test_a_stored_english_title_that_was_lost_is_rewritten_even_when_the_original_matches(url):
    with connect(url) as conn:
        conn.execute("update document set title_original = %s, title_en = '' where url = %s",
                     (TSCHG, ANIMAL_WELFARE_URL))

    with connect(url) as conn:
        report = retitle_all(conn, StubEndpoint({"455": TSCHG}), TranslatingLLM())
        stored = _titles(conn, ANIMAL_WELFARE_URL)

    assert stored == (TSCHG, f"English: {TSCHG}")
    assert report.updated == 1


def test_a_dry_run_names_the_change_without_translating_or_writing(url):
    llm = TranslatingLLM()
    with connect(url) as conn:
        report = retitle_all(conn, StubEndpoint({"455": TSCHG}), llm, dry_run=True)

    with connect(url) as conn:
        stored = _titles(conn, ANIMAL_WELFARE_URL)

    assert stored == ("SR 455", "SR 455")
    assert llm.translated == []
    assert report.changes == (TitleChange(identifier="SR 455", before="SR 455", after=TSCHG),)


def test_a_repaired_title_survives_a_later_failure(url):
    with connect(url) as conn:
        conn.execute("update document set identifier = 'SR 921.0', title_original = 'SR 921.0', "
                     "title_en = 'SR 921.0' where url = %s", (HIKING_URL,))

    endpoint = StubEndpoint({"455": TSCHG, "921.0": "Waldgesetz"})
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, TranslatingLLM(breaks_on="Waldgesetz"))
        conn.rollback()      # whatever retitle did not commit itself is lost, as on a kill

    with connect(url) as conn:
        repaired = _titles(conn, ANIMAL_WELFARE_URL)
        untouched = _titles(conn, HIKING_URL)

    assert repaired == (TSCHG, f"English: {TSCHG}")
    assert untouched == ("SR 921.0", "SR 921.0")
    assert (report.updated, report.failed) == (1, 1)


def test_documents_of_other_sources_are_never_examined(url):
    endpoint = StubEndpoint({"455": TSCHG})
    with connect(url) as conn:
        report = retitle_all(conn, endpoint, TranslatingLLM())
        other = conn.execute(
            "select title_en from document where source_id = 'zh_ch'").fetchone()

    assert other["title_en"] == "Dogs in the Canton of Zurich"
    assert report.examined == 2
