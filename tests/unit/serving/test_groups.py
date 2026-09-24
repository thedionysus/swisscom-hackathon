from datetime import UTC, date, datetime

from swiss_grounding.serving.groups import collapse
from swiss_grounding.serving.models import Candidate

NOW = datetime(2026, 9, 20, tzinfo=UTC)


def cand(lang, rank=1, group="g", align="a", authentic=True, valid_from=None, query_langs=("de",), cid=None):
    return Candidate(
        chunk_id=cid or hash((group, align, lang)) % 10_000, language=lang, document_id=1,
        translation_group_id=group, align_key=align, extent_id="CH", authority="federal_law",
        url=f"https://x/{lang}", anchor=None, title="t", publisher="p", breadcrumb=(), text=f"text {lang}",
        is_authentic=authentic, valid_from=valid_from, valid_to=None, modified_at=None, fetched_at=NOW,
        extraction="native", rrf=1 / (60 + rank), rrf_rank=rank, arms=frozenset({"dense"}),
        query_langs=frozenset(query_langs))


def test_question_language_version_represents_the_group_even_if_not_a_candidate():
    found = [cand("fr", rank=1)]
    versions = {("g", "a"): (cand("de"), cand("fr"), cand("it"), cand("en", authentic=False))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.representative.language == "de"
    assert g.representative.rrf_rank == 1


def test_corroboration_is_the_share_of_other_authentic_versions_found():
    found = [cand("de", 1), cand("fr", 2), cand("en", 3, authentic=False)]
    versions = {("g", "a"): (cand("de"), cand("fr"), cand("it"), cand("en", authentic=False))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.corroboration == 0.5          # fr found, it not; en never counts
    assert g.corroboration_basis == "cross_lingual"


def test_monolingual_group_is_not_applicable():
    [g] = collapse([cand("it")], {("g", "a"): (cand("it"),)}, question_lang="it")
    assert g.corroboration is None and g.corroboration_basis is None


def test_independent_basis_when_each_version_was_found_by_text_in_its_own_language():
    found = [cand("de", 1, query_langs=("de",)), cand("fr", 2, query_langs=("fr",))]
    versions = {("g", "a"): (cand("de"), cand("fr"))}
    [g] = collapse(found, versions, question_lang="de")
    assert g.corroboration == 1.0 and g.corroboration_basis == "independent"


def test_divergent_versions_are_flagged_and_do_not_corroborate():
    found = [cand("de", 1, valid_from=date(2026, 1, 1)), cand("fr", 2, valid_from=date(2025, 1, 1))]
    versions = {("g", "a"): (found[0], found[1])}
    [g] = collapse(found, versions, question_lang="de")
    assert g.versions_diverge is True and g.corroboration == 0.0


def test_without_a_question_language_version_prefer_an_authentic_one():
    found = [cand("en", 1, authentic=False), cand("it", 2)]
    [g] = collapse(found, {("g", "a"): tuple(found)}, question_lang="rm")
    assert g.representative.language == "it" and g.representative.rrf_rank == 1


def test_groups_keep_candidate_order():
    found = [cand("de", 1, group="b"), cand("de", 2, group="a")]
    groups = collapse(found, {}, question_lang="de")
    assert [g.representative.translation_group_id for g in groups] == ["b", "a"]
